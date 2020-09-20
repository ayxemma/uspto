# USPTOProcessXMLGrant.py
# USPTO Bulk Data Parser - Processes XML Grant Files
# Description: Imported to the main USPTOParser.py.  Processes a downloaded grant data files to the extracting.
# Author: Joseph Lee
# Email: joseph@ripplesoftware.ca
# Website: www.ripplesoftware.ca
# Github: www.github.com/rippledj/uspto

# ImportPython Modules
import time
import os
import sys
import traceback

# Import USPTO Parser Functions
import USPTOLogger
import USPTOSanitizer
import USPTOCSVHandler
import USPTOProcessLinks
import USPTOStoreGrantData
import USPTOProcessZipFile

# Function opens the zip file for XML based patent grant files and parses, inserts to database
# and writes log file success
def process_XML_grant_content(args_array):

    # Set the start time of operation
    start_time = time.time()

    logger = USPTOLogger.logging.getLogger("USPTO_Database_Construction")

    # If csv file insertion is required, then open all the files
    # into args_array
    if "csv" in args_array['command_args'] or ("database" in args_array['command_args'] and args_array['database_insert_mode'] == "bulk"):
        args_array['csv_file_array'] = USPTOCSVHandler.open_csv_files(args_array['document_type'], args_array['file_name'], args_array['csv_directory'])

    # Extract the XML file from the ZIP file
    xml_file_contents = USPTOProcessZipFile.extract_xml_file_from_zip(args_array)

    # If xml_file_contents is None or False, then return immediately
    if xml_file_contents == None or xml_file_contents == False:
        return False

    # Create variables needed to parse the file
    xml_string = ''
    patent_xml_started = False
    # read through the file and append into groups of string.
    # Send the finished strings to be parsed
    # Use uspto_xml_format to determine file contents and parse accordingly
    #print "The xml format is: " + args_array['uspto_xml_format']
    if args_array['uspto_xml_format'] == "gXML4":

        # Loop through all lines in the xml file
        for line in xml_file_contents:

            # Decode the line from byte-object
            line = USPTOSanitizer.decode_line(line)

            # This identifies the start of well formed XML segment for patent
            # Grant bibliographic information
            if "<us-patent-grant" in line:
                patent_xml_started = True
                xml_string += "<us-patent-grant>"

            # This identifies end of well-formed XML segement for single patent
            # Grant bibliographic information
            elif "</us-patent-grant" in line:
                patent_xml_started = False
                xml_string += "</us-patent-grant>"
                # Call the function extract data
                processed_data_array = USPTOProcessLinks.extract_data_router(xml_string, args_array)
                # Call function to write data to csv or database
                USPTOStoreGrantData.store_grant_data(processed_data_array, args_array)
                # Reset the xml string
                xml_string = ''

            # This is used to append lines of file when inside single patent grant
            elif patent_xml_started == True:
                # Check which type of encoding should be used to fix the line string
                xml_string += USPTOSanitizer.replace_new_html_characters(line)

    # Used for gXML2 files
    elif args_array['uspto_xml_format'] == "gXML2":

        # Loop through all lines in the xml file
        for line in xml_file_contents:

            # Decode the line from byte-object
            line = USPTOSanitizer.decode_line(line)

            # This identifies the start of well formed XML segment for patent
            # Grant bibliographic information
            if "<PATDOC" in line:
                patent_xml_started = True
                xml_string += "<PATDOC>"

            # This identifies end of well-formed XML segement for single patent
            # Grant bibliographic information
            elif "</PATDOC" in line:
                patent_xml_started = False
                xml_string += "</PATDOC>"

                # Call the function extract data
                processed_data_array = USPTOProcessLinks.extract_data_router(xml_string, args_array)
                # Call function to write data to csv or database
                USPTOStoreGrantData.store_grant_data(processed_data_array, args_array)
                # Reset the xml string
                xml_string = ''

            # This is used to append lines of file when inside single patent grant
            elif patent_xml_started == True:
                # Check which type of encoding should be used to fix the line string
                xml_string += USPTOSanitizer.replace_old_html_characters(line)

    # Close all the open .csv files being written to
    USPTOCSVHandler.close_csv_files(args_array)

    # Set a flag file_processed to ensure that the bulk insert succeeds
    # This should be true, in case the database insertion method is not bulk
    file_processed = True

    # If data is to be inserted as bulk csv files, then call the sql function
    if "database" in args_array["command_args"] and args_array['database_insert_mode'] == 'bulk':
        # Check for previous attempt to process the file and clean database if required
        args_array['database_connection'].remove_previous_file_records(args_array['document_type'], args_array['file_name'])
        # Loop through each csv file and bulk copy into database
        for key, csv_file in list(args_array['csv_file_array'].items()):
            # Load CSV file into database
            file_processed = args_array['database_connection'].load_csv_bulk_data(args_array, key, csv_file)

    if file_processed:
        # Send the information to USPTOLogger.write_process_log to have log file rewritten to "Processed"
        USPTOLogger.write_process_log(args_array)
        if "csv" not in args_array['command_args']:
            # Delete all the open csv files
            USPTOCSVHandler.delete_csv_files(args_array)

        print('[Loaded {0} data for {1} into database. Time:{2} Finished Time: {3} ]'.format(args_array['document_type'], args_array['url_link'], time.time() - start_time, time.strftime("%c")))
        logger.info('Loaded {0} data for {1} into database. Time:{2} Finished Time: {3}'.format(args_array['document_type'], args_array['url_link'], time.time() - start_time, time.strftime("%c")))
        # Return file_processed as success status
        return file_processed
    else:
        print('[Failed to bulk load {0} data for {1} into database. Time:{2} Finished Time: {3} ]'.format(args_array['document_type'], args_array['url_link'], time.time() - start_time, time.strftime("%c")))
        logger.error('Failed to bulk load {0} data for {1} into database. Time:{2} Finished Time: {3} ]'.format(args_array['document_type'], args_array['url_link'], time.time() - start_time, time.strftime("%c")))
        # Return None as failed status during database insertion
        return None
