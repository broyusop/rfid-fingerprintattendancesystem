import RPi.GPIO as GPIO
import MFRC522
import mysql.connector
import datetime
import time
import signal
import hashlib
from pyfingerprint.pyfingerprint import PyFingerprint

mydb = mysql.connector.connect(
  host="192.168.43.99",  #ip of xampp/wampp or pc server
  user="user",
  passwd="1234",
  database='dbname'
)

mycursor = mydb.cursor()
continue_reading = True

try:
	f = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)

	if (f.verifyPassword()==False):
		raise ValueError('The given fingerprint sensor password is wrong')

except Exception as e:
	print ('the fingerprint sensor could not be initialized')
	print ('Exception messeage ' + str(e))
	exit (1)


# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print "Ctrl+C captured, ending read."
    continue_reading = False
    mydb.close()
    #GPIO.cleanup()

def addSecs(tm, secs):
    fulldate = datetime.datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
    fulldate = fulldate + datetime.timedelta(seconds=secs)
    return fulldate.time()

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)

# Create an object of the class MFRC522
MIFAREReader = MFRC522.MFRC522()

#Setup a variable to store the last read chip
lastDetected=""

HOUR  = datetime.datetime.now().hour

# Welcome message
print("Looking for cards")
print("Press Ctrl-C to stop.")

# This loop checks for chips. If one is near it will get the UID
while continue_reading:
	# Scan for cards
	(status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

	# If a card is found
	if status == MIFAREReader.MI_OK:
		print "Card detected"

	# Get the UID of the card
	(status,uid) = MIFAREReader.MFRC522_Anticoll()

	# If we have the UID, continue
	if status == MIFAREReader.MI_OK:

		uid_string = str(uid[0])+"-"+str(uid[1])+"-"+str(uid[2])+"-"+str(uid[3])

		if True: #lastDetected != uid_string:
			# Print UID
			print "##############################"
			print "Employee ID : "+ uid_string

			# Update the variable
			lastDetected = uid_string

			sqlQuery = "SELECT EXISTS(SELECT TagID FROM users WHERE TagID='" + uid_string + "')"
			#print sqlQuery
			mycursor.execute(sqlQuery)

			if mycursor.fetchall()[0][0] is 1:

				try:
					print ('waiting for finger...')

					while (f.readImage()==False):
						pass

					f.convertImage(0x01)

					result = f.searchTemplate()

					positionNumber = str(result[0])


					sqlQuery = "SELECT EXISTS(SELECT TempID FROM users WHERE TempID='"+positionNumber+"' AND TagID= '"+uid_string+"')"
					mycursor.execute(sqlQuery)

					if mycursor.fetchall()[0][0] is 1:
						print "Employee Verified"

						if 5 < HOUR < 24:
							#print "WORKING HOURS!"

							# Check If Tag swiped before on current date
							sqlQuery = "SELECT EXISTS(SELECT TagID FROM attendance WHERE TagID='" + uid_string + "' AND Date=CURDATE())"
							#print sqlQuery
							mycursor.execute(sqlQuery)
			
							if mycursor.fetchall()[0][0] is 1:
								#print "System Detected that you have already logged"
								sqlQuery = "SELECT Status FROM attendance WHERE TagID='" + uid_string + "' AND Date=CURDATE()"
								#print sqlQuery
								mycursor.execute(sqlQuery)
								status = mycursor.fetchall()[0][0]
								if 7 < HOUR < 12:
									if status is 0:
										message = "You cannot CheckIn Twice during MORNING SHIFT!!"
										print(message)

										sqlQuery = "INSERT INTO error_message(message) \
												VALUES('" +message+ "')"
							
										mycursor.execute(sqlQuery)	
										mydb.commit()
										time.sleep(2)		
										sqlQuery = "DELETE FROM error_message"
										mycursor.execute(sqlQuery)
										mydb.commit();

						


									else: # status = 1 CHECK-OUT
										sqlQuery = "SELECT CheckInTime FROM attendance WHERE TagID='" + uid_string + "' AND Date=CURDATE()"
										mycursor.execute(sqlQuery)
										checkedIn_Time = mycursor.fetchall()[0][0]
										a = checkedIn_Time.time()
										b = addSecs(a, 300) # ADD 5min


										if datetime.datetime.now().time() > b:
											message = "Checkout successfully!"
											print(message)
											sqlQuery = "INSERT INTO error_message(message) \
												VALUES('" +message+ "')"
								
											mycursor.execute(sqlQuery)	
											mydb.commit()
											time.sleep(2)		
											sqlQuery = "DELETE FROM error_message"
											mycursor.execute(sqlQuery)
											mydb.commit();


											sqlQuery = "SELECT UploadImage FROM users WHERE TagID='"+uid_string+"'"
											mycursor.execute(sqlQuery)
											image = str(mycursor.fetchall()[0][0])

											sqlQuery = "INSERT INTO output(image, tag_id, status, date_time) \
											VALUES('" +image+ "', '" +uid_string+ "','OUT', NOW())"
											mycursor.execute(sqlQuery)
											mydb.commit()

											# checkout and update status
											sqlQuery = "UPDATE attendance SET CheckOutTime=NOW(), Status=0 WHERE TagID='" + uid_string + "' AND Date=CURDATE()"
											#print sqlQuery
											mycursor.execute(sqlQuery)
											mydb.commit()
										else:
											message =  "Please wait after "+ str(b)+" to checkout"	
											print(message)

											sqlQuery = "INSERT INTO error_message(message) \
												VALUES('" +message+ "')"
								
											mycursor.execute(sqlQuery)	
											mydb.commit()
											time.sleep(2)		
											sqlQuery = "DELETE FROM error_message"
											mycursor.execute(sqlQuery)
											mydb.commit();


								
								else: # if 13 < HOUR < 17
									if status is 2:
										message =  "You cannot CheckIn Twice during AFTERNOON SHIFT!"
										print(message)
										sqlQuery = "INSERT INTO error_message(message) \
											VALUES('" +message+ "')"
									
										mycursor.execute(sqlQuery)	
										mydb.commit()
										time.sleep(2)		
										sqlQuery = "DELETE FROM error_message"
										mycursor.execute(sqlQuery)
										mydb.commit();

							

									if status is 0:
										#print "CheckedOut (MORNING).. CheckIN NOW"
										print "AFTERNOON SHIFT!"
										sqlQuery = "UPDATE attendance SET CheckInTime1=NOW(), Status=1 WHERE TagID='" + uid_string + "' AND Date=CURDATE()"
										#print sqlQuery
										mycursor.execute(sqlQuery)
										mydb.commit()
									#elif status == 1:
									if status is 1:					
										sqlQuery = "SELECT CheckInTime1 FROM attendance WHERE TagID='" + uid_string + "' AND Date=CURDATE()"
										mycursor.execute(sqlQuery)
										checkedIn_Time1 = mycursor.fetchall()[0][0]
										a = checkedIn_Time1.time()
										b = addSecs(a, 300) # ADD 5min

										if datetime.datetime.now().time() > b:
							
											message = "Checkout successfully!"
											print(message)

											sqlQuery = "INSERT INTO error_message(message) \
												VALUES('" +message+ "')"
								
											mycursor.execute(sqlQuery)	
											mydb.commit()
											time.sleep(2)		
											sqlQuery = "DELETE FROM error_message"
											mycursor.execute(sqlQuery)
											mydb.commit();

						
											sqlQuery = "SELECT UploadImage FROM users WHERE TagID='"+uid_string+"'"
											mycursor.execute(sqlQuery)
											image = str(mycursor.fetchall()[0][0])

											insertQuery = "INSERT INTO output(image, tag_id, status, date_time) \
											VALUES('" +image+ "', '" +uid_string+ "','OUT', NOW())"

											mycursor.execute(insertQuery)
									
											today = str(datetime.datetime.now())	

											#print(today)
											sqlQuery1 = "UPDATE attendance SET CheckoutTime1='"+today+"', Status=2 WHERE TagID='" +uid_string+ "' AND Date=CURDATE()"

											mycursor.execute(sqlQuery1)
											mydb.commit()
										else:
											message = "Please wait after "+ str(b)+" to checkout"
											print(message)
											sqlQuery = "INSERT INTO error_message(message) \
												VALUES('" +message+ "')"
								
											mycursor.execute(sqlQuery)	
											mydb.commit()
											time.sleep(2)		
											sqlQuery = "DELETE FROM error_message"
											mycursor.execute(sqlQuery)
											mydb.commit();

						
							else:    
						                                                                                                                                                                                                                                                                                                                                    
								message =  "Checkin successfully!"
								print(message)
								sqlQuery = "INSERT INTO error_message(message) \
									VALUES('" +message+ "')"
								mycursor.execute(sqlQuery)	
								mydb.commit()
								time.sleep(2)		
								sqlQuery = "DELETE FROM error_message"
								mycursor.execute(sqlQuery)
								mydb.commit();

								if 7 < HOUR < 12:
									#print(uid_string)
									sqlQuery="SELECT id, UploadImage  FROM users WHERE TagID='"+uid_string+"'"
									#print(sqlQuery)
									mycursor.execute(sqlQuery)						
									a = mycursor.fetchall()
									#print(a)
									PkId = str(a[0][0])

									sqlQuery = "SELECT UploadImage FROM users WHERE TagID='"+uid_string+"'"
									mycursor.execute(sqlQuery)
									image = str(mycursor.fetchall()[0][0])
								
									sqlQuery = "INSERT INTO output(image, tag_id, status, date_time) \
									VALUES('" +image+ "', '" +uid_string+ "','IN', NOW())"
									mycursor.execute(sqlQuery)
									mydb.commit()							

									print "MORNING SHIFT!"
									sqlQuery = "INSERT INTO attendance( FkEmployeeId, TagID, Date, CheckInTime, Status) \
											VALUES( '" +PkId+ "', '" +uid_string+ "', CURDATE(), NOW(), 1)"
									#print sqlQuery                        
									mycursor.execute(sqlQuery)
									mydb.commit()

								elif 12 <= HOUR < 24:
									#print(uid_string)
									sqlQuery="SELECT id FROM users WHERE TagID='"+uid_string+"'" 
									mycursor.execute(sqlQuery)
								
									PkId = str(mycursor.fetchall()[0][0])
									sqlQuery = "SELECT UploadImage FROM users WHERE TagID='"+uid_string+"'"
									mycursor.execute(sqlQuery)
									image = str(mycursor.fetchall()[0][0])
						
									sqlQuery = "INSERT INTO output(image, tag_id, status, date_time) \
									VALUES('" +image+ "', '" +uid_string+ "','IN', NOW())"

									mycursor.execute(sqlQuery)
									mydb.commit()


									print "AFTERNOON SHIFT!"
									sqlQuery = "INSERT INTO attendance(FkEmployeeId, TagID, Date, CheckInTime1, Status) \
										VALUES(" +PkId+ ", '" +uid_string+ "', CURDATE(), NOW(), 1)"
								#print sqlQuery                        
									mycursor.execute(sqlQuery)	
									mydb.commit()

								else:
									message = "You can't Checkin during this hours!"
									print(message)

									sqlQuery = "INSERT INTO error_message(message) \
										VALUES('" +message+ "')"
								
									mycursor.execute(sqlQuery)	
									mydb.commit()
									time.sleep(2)		
									sqlQuery = "DELETE FROM error_message"
									mycursor.execute(sqlQuery)
									mydb.commit();

						


						time.sleep(3)
					
					else:
						message =  ('Matching failed')
						sqlQuery = "INSERT INTO error_message(message) \
										VALUES('" +message+ "')"
								
									mycursor.execute(sqlQuery)	
									mydb.commit()
									time.sleep(2)		
									sqlQuery = "DELETE FROM error_message"
									mycursor.execute(sqlQuery)
									mydb.commit();

						pass

				except Exception as e:
					print ('operation failed')
					print ('exception message:' + str(e))
					exit(1)
			else:

				message =  "You are not a verified employee. Please contact the admin"
				print(message)
				sqlQuery = "INSERT INTO error_message(message) \
					VALUES('" +message+ "')"
				print(sqlQuery)
				mycursor.execute(sqlQuery)	
				mydb.commit()
				time.sleep(2)
				sqlQuery = "DELETE FROM error_message"
				mycursor.execute(sqlQuery)
				mydb.commit();


