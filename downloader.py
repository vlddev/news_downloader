import sys
import traceback
import importlib
import threading
import logging
import downloader_common

# import downloader_champion


def mode1():
    rootPath = downloader_common.rootPath
    dateFrom = '01.01.2019'
    dateTo = '01.07.2019'

    dlModules = [
        'downloader_up_news',  'downloader_eurointegration',
        'downloader_gazeta_ua', 'downloader_lb',
        'downloader_unian', 'downloader_zaxid', 'downloader_zik',
        # 'downloader_champion', 'downloader_epravda', 'downloader_dt_news'
    ]

    for dlModule in dlModules:
        try:
            DownloaderClass = getattr(importlib.import_module(dlModule), "Downloader")
            downloader = DownloaderClass(rootPath)
            job = threading.Thread(target=downloader.load, args=(dateFrom, dateTo))
            job.start()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error in " + dlModule + ": ", exc_type)
            print("Error in " + dlModule + ": ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)


def mode2():
    rootPath = downloader_common.rootPath
    dlModules = [('downloader_zbruc', '01.01.1893', '01.04.1893'),
                 ('downloader_zbruc', '01.01.1918', '01.04.1918'),
                 ('downloader_zbruc', '01.01.1943', '01.01.1943')]

    for dlModule, dateFrom, dateTo in dlModules:
        try:
            DownloaderClass = getattr(
                importlib.import_module(dlModule), "Downloader")
            downloader = DownloaderClass(rootPath)
            job = threading.Thread(
                target=downloader.load, args=(dateFrom, dateTo))
            job.start()
        except BaseException:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error in " + dlModule + ": ", exc_type)
            print("Error in " + dlModule + ": ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)


def mode3():
    dlModules = [
        'downloader_day', 'downloader_dt_gazeta', 'downloader_umoloda', 'downloader_molbuk'
    ]

    for dlModule in dlModules:
        try:
            DownloaderClass = getattr(
                importlib.import_module(dlModule), "Downloader")
            downloader = DownloaderClass()
            job = threading.Thread(target=downloader.load)
            job.start()
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error in " + dlModule + ": ", exc_type)
            print("Error in " + dlModule + ": ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)

def mode4():
    rootPath = downloader_common.rootPath
    dlModules = [('downloader_dt_news', '01.01.2014', '01.02.2014'),
                 ('downloader_dt_news', '01.02.2014', '01.03.2014'),
                 ('downloader_dt_news', '01.03.2014', '01.04.2014'),
                 ('downloader_dt_news', '01.04.2014', '01.05.2014'),
                 ('downloader_dt_news', '01.05.2014', '01.06.2014'),
                 ('downloader_dt_news', '01.06.2014', '01.07.2014'),
                 ('downloader_dt_news', '01.07.2014', '01.08.2014'),
                 ('downloader_dt_news', '01.08.2014', '01.09.2014'),
                 ('downloader_dt_news', '01.09.2014', '01.10.2014'),
                 ('downloader_dt_news', '01.10.2014', '01.11.2014'),
                 ('downloader_dt_news', '01.11.2014', '01.12.2014'),
                 ('downloader_dt_news', '01.12.2014', '01.01.2015')]

    for dlModule, dateFrom, dateTo in dlModules:
        try:
            DownloaderClass = getattr(
                importlib.import_module(dlModule), "Downloader")
            downloader = DownloaderClass(rootPath)
            job = threading.Thread(
                target=downloader.load, args=(dateFrom, dateTo))
            job.start()
        except BaseException :
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error in " + dlModule + ": ", exc_type)
            print("Error in " + dlModule + ": ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)


# set params and run manually in following downloaders
# downloader_tyzhden
# downloader_gaz_po_ukr
# downloader_journal_krajina

# ================= main call =======================
logging.basicConfig(
    filename='downloader.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s',
    datefmt='%d.%m.%Y %H:%M:%S')
mode3()
