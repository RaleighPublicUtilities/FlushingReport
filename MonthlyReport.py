## Script for monthly report on SewerFlushing

import arcpy, os, sys, csv, datetime, time, smtplib, logging
from datetime import date
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import formatdate
from email import Encoders
from arcpy import env

env.workspace = "Database Connections/MOBILE_EDIT_VERSION_TESTDB.sde"
# output directory
outDir = "C:/data/" #Change this path if necessary

# related table and fields information
# Gravity Main
GM_table = "RPUD.SewerMainFlushing"
GM_outFile = "GravityMainFlushingReport"
GM_field_alias = ["REPORT DATE", "PU NUMBER", "CREW", "TEAM MEMBER", "TRUCK", "TASK", "FACILITYID", "DEBRIS", "ROOTS", "GREASE", "PIPE MATERIAL", "PIPE SIZE", "MH DIRECTION", "MH MATERIAL", "MH CONDITION", "NOZZLE", "FOOTAGE", "WEATHER", "JOB TYPE", "CUSTOMER CONTACT", "INVENTORY INFO", "CCTV FOLLOWUP", "REPAIR FOLLOWUP", "COMMENTS", "TIME START", "TIME END", "DURATION"]
GM_field_names = ["REPORT_DATE", "PU_NUM", "CREW", "TEAM_MEMBER", "TRUCK", "TASK", "FACILITYID", "DEBRIS", "ROOTS", "GREASE", "PIPE_MATL", "PIPE_SIZE", "MH_DIR", "MH_MATL", "MH_COND", "NOZZLE", "FOOTAGE", "WEATHER", "TYPE", "CUST_CONTACT", "INV_INFO", "CCTV", "REPAIR", "COMMENTS", "TIME_START", "TIME_END", "DURATION"]
# Mainhole
MH_table = "RPUD.SewerMHFlushing"
MH_outFile = "ManholeFlushingReport"
MH_field_alias = ["REPORT DATE", "PU NUMBER", "FACILITYID", "TRUCK", "CREW LEADER", "TEAM MEMBER", "JOB TASK", "MH MATERIAL", "MH CONDITION", "DEBRIS", "ROOTS", "GREASE", "NOZZLE TYPE", "WEATHER", "JOB TYPE", "CUSTOMER CONTACT", "TIME START", "TIME END", "COMMENTS", "CCTV FOLLOWUP", "REPAIR FOLLOWUP", "INVENTORY INFO", "DURATION"]
MH_field_names = ["REPORT_DATE", "PU_NUM", "FACILITYID", "TRUCK_NUM", "CREW", "TEAM_MEMBER", "TASK", "MH_MATL", "MH_COND", "DEBRIS", "ROOTS", "GREASE", "NOZZLE", "WEATHER", "TYPE", "CUST_CONTACT", "TIME_START", "TIME_END", "COMMENTS", "CCTV", "REPAIR", "INV_INFO", "DURATION"]


logging.basicConfig(filename=os.path.join(os.path.dirname(sys.argv[0]), 'monthlyupdate.log'), level=logging.INFO, format='%(asctime)s %(message)s')
# log message to keep track
def logMessage(msg):
    print time.strftime("%Y-%m-%d %H:%M:%S ", time.localtime()) + msg
    logging.warning(msg)
    return

# send email
def SendEmail(fPaths, isAttachmt, body, toList, ccList, bccList, subject):
	
	HOST = "cormailgw.raleighnc.gov"
	#FROM = "joe.li@raleighnc.gov"
	FROM = "PubUtilGIS@raleighnc.gov"
	TO = toList
	CC = ccList
	BCC = bccList
	msg = MIMEMultipart()
	msg['FROM'] = FROM 
	msg['TO'] = TO
	msg['CC'] = CC
	msg['BCC'] = BCC
	msg['Date'] = formatdate(localtime = True)
	msg['Subject'] = subject
	msg.attach(MIMEText(body))
	if isAttachmt:
		for fPath in fPaths:
			part = MIMEBase('text/plain', 'octet-stream')
			part.set_payload(open(fPath, 'rb').read())
			Encoders.encode_base64(part)
			part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(fPath))
			msg.attach(part)
			print ("message attached")
	server = smtplib.SMTP(HOST)
	print ("Connected to server")
	server.sendmail(FROM, TO.split(",") + CC.split(",") + BCC.split(","), msg.as_string())
	print ("Sending Email...")
	server.close()
	for fPath in fPaths:
		os.remove(fPath)	
	print ("Email sent")

# query and export to csv file
def exportToCSV(field_alias, field_names, table, outFile, outDir):
	#calculate date and local timestamp 
	firstDayofM = date(date.today().year, date.today().month, 1).strftime('%Y%m%d')
	firstDayofLM = date(date.today().year, date.today().month - 1, 1).strftime('%Y%m%d')
	thisMonth = datetime.datetime(int(firstDayofM[:4]), int(firstDayofM[4:6]), int(firstDayofM[6:]), 00, 00, 00) + datetime.timedelta(hours=4)
	lastMonth = datetime.datetime(int(firstDayofLM[:4]), int(firstDayofLM[4:6]), int(firstDayofLM[6:]), 00, 00, 00) + datetime.timedelta(hours=4)
	print thisMonth
	print lastMonth
	#build query clause
	whereClause = '"CREATED_DATE" < timestamp \'{0}\' AND "CREATED_DATE" >= timestamp \'{1}\' ORDER BY CREATED_DATE'.format(str(thisMonth), str(lastMonth))
	print whereClause	
	arcpy.MakeQueryTable_management(table, 'queryTable' + table, "NO_KEY_FIELD", "", "", whereClause)
	recordNum = arcpy.GetCount_management('queryTable' + table)
	logMessage(str(recordNum) + " " + table + " reports for " + (lastMonth).strftime("%b, %Y"))
	#list fields
	fields = arcpy.ListFields('queryTable' + table)

	#write to csv
	outFullFile = outFile + "_" + lastMonth.strftime("%Y%m") + ".csv"
	with open(os.path.join(outDir, outFullFile), 'wb') as f:
		w = csv.writer(f)
		w.writerow(field_alias)
		rows = arcpy.SearchCursor("queryTable" + table)
		row = rows.next()
		for row in rows:
			field_vals = []
			for field in fields:
				if field.name in field_names:
					#remove none and invalid value and convert utc time to local
					if row.getValue(field.name) == None:
						field_val = ""
					elif field.type == "Date":
						if row.getValue(field.name).year == 1899:
							field_val = ""
						else:
							field_val = (row.getValue(field.name) - datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
						# if field.name == "REPORT_DATE":
						# 	field_val = (row.getValue(field.name) - datetime.timedelta(hours=4)).strftime("%Y-%m-%d")
					else:
						field_val = row.getValue(field.name)
					field_vals.append(field_val)
			w.writerow([s.encode('utf-8') if type(s) is unicode else s for s in field_vals])
		del row
		del rows
	f.close()

	return recordNum, outFullFile


## main
logMessage("******************Export Flushing Report******************")

GMCount, GMAttach = exportToCSV(GM_field_alias, GM_field_names, GM_table, GM_outFile, outDir)
MHCount, MHAttach = exportToCSV(MH_field_alias, MH_field_names, MH_table, MH_outFile, outDir)
attachList = [os.path.join(outDir, GMAttach), os.path.join(outDir, MHAttach)]
lastMonth = date(date.today().year, date.today().month - 1, 1)

emailSub = "Monthly Flushing Report Summary"
message = "Attached please find Flushing Monthly Summary for " + lastMonth.strftime("%b, %Y")
message += "\n\nGravity Main Flushing reports: {1}\nManhole Flushing reports: {2}".format(lastMonth.strftime("%b, %Y"), GMCount, MHCount)
message += "\n\nThanks,\n"
message += "PUGIS"

# email to send in test
to = "joe.li@raleighnc.gov"
cc = ""
bcc = ""
# email to send in production
# to = "jeffrey.bognar@raleighnc.gov"
# cc = "david.jackson@raleighnc.gov, chris.mosley@raleighnc.gov, dustin.tripp@raleighnc.gov" #tom.johnson@raleighnc.gov" ## email copy list
# bcc = "joe.li@raleighnc.gov" #to notify GIS team 
# message to print
isAttach = True
print 'Formatting email...'
print '-' * 80
print 'Subject: {}'.format(emailSub)
print 'Message: {}'.format(message)
if isAttach:
	print 'Attachment: {}, {}'.format(attachList[0], attachList[1])
print '-' * 80


# send daily report to Sewer Team Manager
SendEmail(attachList, isAttach, message, to, cc, bcc, emailSub)
logMessage("Email sent to sewer")
