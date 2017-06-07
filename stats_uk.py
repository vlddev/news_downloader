#!/usr/bin/python

import MySQLdb
from MySQLdb import cursors
from math import sqrt
import sys

def computeYearlyStatsDeviation(db):
    # prepare a cursor object using cursor() method
    cursor = db.cursor()
    sql = """SELECT word, cnt2000, cnt2001, cnt2002, cnt2003, cnt2004, cnt2005, cnt2006, cnt2007, cnt2008, cnt2009, cnt2010, cnt2011, cnt2012, cnt2013, cnt2014, cnt2015, cnt2016
            FROM stats_yearly"""

    try:
        devDict = {}
        # Execute the SQL command
        cursor.execute(sql)
        row = cursor.fetchone()
        while row is not None:
            #compute deviation
            i = 0
            summe = 0
            for col in row:
                if i != 0 and col is not None:
                    summe = summe + col
                i = i + 1

            average = summe/(i-1)
            #print('i = '+str(i)+', sum = '+str(summe)+', average = '+str(average))

            deviation = 0.0
            if average != 0.0 :
                summe = 0.0
                i = 0
                for col in row:
                    if i != 0 and col is not None:
                        summe = summe + (col/average - 1)*(col/average - 1)
                    i = i + 1

                deviation = sqrt(summe/(i-1))
            #print('deviation = '+str(deviation))
            devDict[row[0]] = deviation

            row = cursor.fetchone()
            #break


        for key, value in devDict.items():
            #update db row
            #updSql = "UPDATE stats_yearly SET deviation = "+str(value)+" WHERE word = '"+key+"'"
            #print(updSql)
            cursor.execute("UPDATE stats_yearly SET deviation = %s WHERE word = %s", (value, key))

        print("dict size = %d", len(devDict))
        cursor.close()
        # Commit your changes in the database
        db.commit()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        # Rollback in case there is any error
        db.rollback()

def computeRankStats(db, percent):
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    try:
        print ('Ranks for %d%% words.' % (percent))
        print ('Year\t%\tRank')
        print ('---------------------')
        for year in range(1997, 2017) :
            cursor.execute('SELECT sum(cnt%d) FROM stats_yearly' % (year))
            row = cursor.fetchone()
            if row is None:
                print ("Sum for year %d is epmty" % (year));
                break;

            freqSum = row[0]
            cursor.execute('SET @rank := 0, @total := 0')
            sql = 'SELECT word, @total := @total + cnt AS total, @total*100/%f AS percent, @rank := @rank + 1 AS rank ' % (freqSum)
            sql = sql + 'FROM (SELECT word, cnt%d AS cnt FROM stats_yearly ORDER BY cnt%d desc ) AS st1 ' % (year,year)
            sql = sql + 'WHERE @total*100/%f <= %d ' % (freqSum,percent)
            #print (sql)
            cursor.execute(sql)
            #fetch to last row
            row = cursor.fetchone()
            lastRow = row
            while row is not None:
                row = cursor.fetchone()
                if row is not None:
                    lastRow = row
            if lastRow is None:
                print ("Stats for year %d is epmty" % (year));
                break;
            print ('{:d}\t{:f}\t{:d}'.format(year,lastRow[2],lastRow[3]))

        cursor.close()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        # Rollback in case there is any error
        db.rollback()

def computeWordRanks(db,db1):
    # prepare a cursor object using cursor() method
    cursor = db.cursor()
    updCursor = db1.cursor()

    try:
        for year in range(1991, 2017) :
            print ("process year %d" % (year));
            sqlSel = """SELECT s.word, s.cnt%d, @rownum := @rownum + 1 AS rank
                            FROM stats_yearly s
                            WHERE s.cnt%d is not null
                            ORDER BY 2 desc""" % (year,year)
            sqlUpd = 'INSERT INTO rank_yearly (word, cnt'+str(year)+') VALUES (%s, %s) ON DUPLICATE KEY UPDATE cnt'+str(year)+'=%s'
            print (sqlUpd)
            cursor.execute('SET @rownum := 0')
            cursor.execute(sqlSel)
            row = cursor.fetchone()
            while row is not None:
                rank = row[2]
                updCursor.execute(sqlUpd, (row[0],rank,rank))
                #print ("rank %d" % (row[1]))
                row = cursor.fetchone()
            db1.commit()

        cursor.close()
        updCursor.close()
        db1.commit()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        # Rollback in case there is any error
        db1.rollback()

# Open database connection
db = MySQLdb.connect(user="root",
                     passwd="lacrimosa",
                     db="uk",
                     charset='utf8',
                     cursorclass = MySQLdb.cursors.SSCursor
                     )
db1 = MySQLdb.connect(user="root",
                     passwd="lacrimosa",
                     db="uk",
                     charset='utf8',
                     cursorclass = MySQLdb.cursors.SSCursor
                     )
#computeYearlyStatsDeviation(db)
#computeRankStats(db, 80)
#computeRankStats(db, 85)
#computeRankStats(db, 90)
#computeRankStats(db, 95)
computeWordRanks(db, db1)

# disconnect from server
db.close()
db1.close()
