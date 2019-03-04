# SendToSFWave
### This script can be used to push data from databases using JDBC connectivity, to Salesforce Analytic datasets.

1. Prepare your data:
    - Remove commas and currencies from numeric values, so they do not load as dimension values
    - Check column headers, to ensure correct labels.  If they are not correct, change labels in the metadata.
    - Ensure date values are in a supported format.  Date format is automatically determined from the first rows of the CSV file.  If a format cannot be determined, European is used.  Check documentation for a list of supported date formats.
    - When values contain commas, new lines, or double quotes, enclose them in double quotes *Should be handled automatically in MS Excel
    - Escape a double quote in a value by preceding it with a double quote *Should be handled automatically in MS Excel
    - Ensure at least one column contains dimension values.
    - Columns with no values in first 100 rows default to a measure
    - 50K row limit for a single CSV file.  Can create multiple datasets and join them together to work around
    - Save your data source information and SQL required for the extraction.
2. Log into Salesforce and create a Dataset as described in the [Salesforce documentation](https://help.salesforce.com/articleView?id=bi_dataset_create.htm&type=5). 
3. Save the generated Data Schema file (Action button next to the generated file name). 

#### NOTE: If you need to modify the Data Schema file, do so before you proceed. For example, if you need to define a default value for null fields, edit the json to reflect that and replace it.

#### Original field definition:

```json

{
    "fullyQualifiedName": "Remote_Support_Satisfaction",
    "name": "Remote_Support_Satisfaction",
    "type": "Text",
    "label": "Remote_Support_Satisfaction"
},
    
```

#### Edited field definition:

```json

{
    "fullyQualifiedName": "Remote_Support_Satisfaction",
    "name": "Remote_Support_Satisfaction",
    "type": "Numeric",
    "label": "Remote_Support_Satisfaction",
    "isSystemField": false,
    "defaultValue": "0",
    "isUniqueId": false,
    "precision": 5,
    "scale": 0 
},

```

4. Add the Data Set to the shared App in Einstein and ensure the user that will be uploading the data has Edit rights in the App.
5. Clone/download the GitHub project SendToSFWave.
6. See the commented "sudo yum" commands at the top of SendData.py. Ensure you have these packages installed.
7. Edit SendData.py and change the variable sf_username to reflect the user login you will be using to update this data set.
8. Edit SendData.py and change the variable sf_url to be the production/sandbox/custom Salesforce URL you connect to.
9. Edit SendData.py and change the variable sf_dataset_apiname, found by Editing the data set in Einstein.
10. Edit SendData.py and change the variable sf_dataset_lablename, found by Editing data set in Einstein.
11. Copy the json Data Schema file you downloaded in step 3 to the metadata folder in the SendToSFWave project space, and update the metadata variable in SendData.py to reflect the new file name.
12. Edit secret.py to reflect your sf_client_id, sf_client_secret, sf_password and dsn_password.
13. Compile secret.py; 
    python -m py_compile secret.py
14. Edit the database connection variables dsn_database, dsn_hostname, dsn_port, dsn_uid, jdbc_driver_name, jdbc_short_driver_name and jdbc_driver_loc for your environment.
15. Copy your SQL query into the sql variable.
16. Test in your favorite debugger, or kick it off and check errlog.txt for your results.
