# RHEL
# sudo yum install python-devel
# sudo pip install ibm_db
# sudo pip install simple_salesforce
# sudo pip install jaydebeapi
# sudo yum install yum install java-1.6.0-openjdk

# Ubuntu
# sudo apt-get install python-dev
# sudo python -m pip install ibm_db
# sudo python -m pip install simple_salesforce - 
#   newer versions of pip may need to be invoked as; sudo python -m pip install "git+https://github.com/simple-salesforce/simple-salesforce"
# sudo python -m pip install jaydebeapi
# sudo apt-get install default-java

from simple_salesforce import Salesforce
import requests
import jaydebeapi
import sys
import csv
import base64
import os
import tempfile
import math

#----------------------------
# add your secret variables to the secret.py file, e.g. sf_client_id = ""
# this python file should be compiled and the plain text version deleted
# python -m py_compile secret.py
#----------------------------
import secret

#----------------------------
# set up some variables
# fname is the temp data export 
# from your source used to feed SF Data Set
#----------------------------
debug = True
fname = "./data/temp.csv"
errlog = "./log/errorlog.txt"

#----------------------------
# Salesforce conn info
#----------------------------
sf_grant_type = "password"
sf_username = "myusername"
sf_url = "https://test.salesforce.com"

#----------------------------
# build the parameter set for SFDC login
#----------------------------
params = {
    "grant_type": sf_grant_type,
    "client_id": secret.sf_client_id,
    "client_secret": secret.sf_client_secret,
    "username": sf_username,
    "password": secret.sf_password
}

#----------------------------
# Salesforce dataset info
# See readme.md for details
#----------------------------
sf_dataset_apiname = "medallia_sf_surveys_ext"
sf_dataset_lablename = "Medallia Surveys"
metadata = "./metadata/SfdcMedalliaMetadata.json"

#----------------------------
# Database conn info
# Set these parameters
#----------------------------
dsn_database = "mydatabase"
dsn_hostname = "myhost.ibm.com"
dsn_port = "2222"
dsn_uid = "myuid"
dsn_pwd = secret.dsn_pwd
jdbc_driver_name = "org.netezza.Driver"
jdbc_short_driver_name = "netezza"
jdbc_driver_loc = "./drivers/nzjdbc.jar"

#----------------------------
# Build the connection string
#----------------------------
###jdbc:netezza://',server + "/',dbName ;
connection_string = 'jdbc:'+jdbc_short_driver_name+'://'+dsn_hostname+':'+dsn_port+'/'+dsn_database
url = '{0}:user={1};password={2}'.format(connection_string, dsn_uid, dsn_pwd)

if debug: print 'URL: ', format(url)
if debug: print 'Connection String: ', format(connection_string)

#----------------------------
# Query your data source
#----------------------------
sql = ("select promoter_type, survey_response_date, survey_id, likelihood_to_recommend, support_satisfaction, ticket_num from MEDALLIA.DRILL_SURVEY")

#----------------------------
# Connect to data source
#----------------------------
try:
    conn = jaydebeapi.connect(jdbc_driver_name, connection_string, {'user': dsn_uid, 'password': dsn_pwd}, jars=jdbc_driver_loc)
    curs = conn.cursor()
except jaydebeapi.Error as e:
    if debug: print 'Error in connecting to the database.'
    with open(errlog, "wb") as errlg:
        errlg.writelines("Error in connecting to the database.")
        errlg.writelines(e)
        errlg.flush()
        exit()

#----------------------------
# Split the results into 10mb chunnks
# Split function found here: https://stackoverflow.com/questions/30947682/splitting-a-csv-file-into-equal-parts
#----------------------------
def split(infilename, num_chunks):
    READ_BUFFER = 2**13
    in_file_size = os.path.getsize(infilename)
    if debug: print 'SPLIT() in_file_size:', in_file_size
    chunk_size = in_file_size // num_chunks
    if debug: print 'SPLIT(): target chunk_size:', chunk_size
    files = []
    with open(infilename, 'rb', READ_BUFFER) as infile:
        for _ in xrange(num_chunks):
            temp_file = tempfile.TemporaryFile()
            while temp_file.tell() < chunk_size:
                try:
                    temp_file.write(infile.next())
                except StopIteration:  # end of infile
                    break
            temp_file.seek(0)  # rewind
            files.append(temp_file)
    return files

#----------------------------
# fetch the data
#----------------------------
try:
    curs.execute(sql)
    result = curs.fetchall()
    # get the column names for writing the csv header
    col_names = [i[0] for i in curs.description]
    if debug: print 'Total records fetched : ',str(len(result))
except jaydebeapi.Error as e:
    if debug: print 'Error in fetching database results.'
    with open(errlog, "wb") as errlg:
        errlg.write("Error in fetching database results.")
        errlg.write(e)
        errlg.flush()
        exit()
finally:
    # clean up the connection
    curs.close()
    conn.close()

#----------------------------
# write results to csv
#----------------------------
with open(fname, "wb") as myfile:
    wrtr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    # write the csv header
    wrtr.writerow([g for g in col_names])
    for row in result:
        wrtr.writerow([unicode(s).encode("utf-8").strip('None') for s in row])
        myfile.flush()

#----------------------------
# Log into Salesforce
#----------------------------
try:
    # make the request and get the access_token and instance_url for future posts
    r = requests.post(
        sf_url + "/services/oauth2/token", params=params)
    # store the tocken and instance url
    access_token = r.json().get("access_token")
    instanceUrl = r.json().get("instance_url")
    if debug: print 'Login to Salesforce : access token is ',str(access_token)
except Exception as e:
    if debug: print 'Error in logging into Salesforce.'
    with open(errlog, "wb") as errlg:
        errlg.write("Error posting Auth request to Salesforce.")
        errlg.write(e)
        errlg.flush()
        exit()

#----------------------------
# instantiate the sf object for easy crud operations
#----------------------------
sf = Salesforce(instance_url=instanceUrl, session_id=access_token)

#----------------------------
# set up the data header by including the data description
#----------------------------
with open(metadata, "r") as mdata:
        mdata_contents = base64.b64encode(str(mdata.read()))

#----------------------------
# insert the header record
#----------------------------
try:
    res_header = sf.InsightsExternalData.create({
        'Format': 'Csv',
        'EdgemartAlias': 'MedalliaSurveys',
        'EdgemartLabel': 'Medallia Surveys',
        'Description': 'Test of API load.',
        'FileName': 'MedalliaSurveys',
        'MetadataJson': mdata_contents,
        'Operation': 'Overwrite',
        'Action': 'None'
    })
    #----------------------------
    # retrieve the new header id for use with the data parts
    header_id = res_header.get('id')
    if debug: print 'Created data header. Id is ',str(header_id)
except Exception as e:
    if debug: print 'Error in writing data header.'
    with open(errlog, "wb") as errlg:
        errlg.write("Error writing data header to Salesforce.")
        errlg.write(str(e))
        errlg.flush()
        exit()

#----------------------------
# if the file is larger than 10mb,
# it needs to be broken up in chunks
#----------------------------
fsize = os.stat(fname).st_size

try:
    if (fsize > 10000000):
        if debug: print 'File needs to be chunked, size is : ',str(fsize)
        num_chunks = int(math.ceil(float(fsize) / float(10000000)))
        files = split(fname, num_chunks)
        if debug: print 'Number of files created: ', format(len(files))
        for i, ifile in enumerate(files, start=1):
            f_contents = base64.b64encode(str(ifile.read()))
            res_data = sf.InsightsExternalDataPart.create({
                    'DataFile': f_contents,
                    'InsightsExternalDataId': header_id,
                    'PartNumber': str(i)
                })
    else:
        if debug: print 'File is fine to post in single part.'
        # base64 encode the data file
        with open(fname, "r") as f:
            f_contents = base64.b64encode(str(f.read()))
            res_data = sf.InsightsExternalDataPart.create({
                'DataFile': f_contents,
                'InsightsExternalDataId': header_id,
                'PartNumber': '1'
            })
        if debug: print 'The data part created is : ',str(res_data.get('id'))
except Exception as e:
    if debug: print 'Error in writing data part.'
    with open(errlog, "wb") as errlg:
        errlg.write("Error writing data part to Salesforce.")
        errlg.write(str(e))
        errlg.flush()
        exit()

#----------------------------
# Finalize the process
#----------------------------
try:
    res_proc = sf.InsightsExternalData.update(header_id, {
    'Action': 'Process'
        })
    if debug: print 'The result of the processing the data is : ',str(res_proc)
except Exception as e:
    if debug: print 'Error in Updating action of data header.' 
    with open(errlog, "wb") as errlg:
        errlg.write("Error processing data in Salesforce.")
        errlg.write(str(e))
        errlg.flush()
        exit()    
