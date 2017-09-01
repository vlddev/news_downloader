import sys
import traceback
import importlib
import threading
import logging
import downloader_common
# import downloader_champion


def mode1():
    rootPath = downloader_common.rootPath
    dateFrom = '01.07.2017'
    dateTo = '01.09.2017'

    dlModules = ['downloader_champion', 'downloader_up_news', 'downloader_epravda', 'downloader_dt_news',
                 'downloader_gazeta_ua', 'downloader_lb', 'downloader_unian', 'downloader_zaxid', 'downloader_zik']

    for dlModule in dlModules:
        try:
            DownloaderClass = getattr(importlib.import_module(dlModule), "Downloader")
            downloader = DownloaderClass(rootPath)
            job = threading.Thread(target=downloader.load, args=(dateFrom, dateTo))
            job.start()
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error in "+dlModule+": ", exc_type)
            print ("Error in "+dlModule+": ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)


def mode2():
    rootPath = downloader_common.rootPath
    dlModules = [('downloader_zbruc', '01.06.1892', '26.08.1892'),
                 ('downloader_zbruc', '01.06.1917', '26.08.1917'),
                 ('downloader_zbruc', '01.06.1942', '26.08.1942')]

    for dlModule, dateFrom, dateTo in dlModules:
        try:
            DownloaderClass = getattr(importlib.import_module(dlModule), "Downloader")
            downloader = DownloaderClass(rootPath)
            job = threading.Thread(target=downloader.load, args=(dateFrom, dateTo))
            job.start()
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error in "+dlModule+": ", exc_type)
            print ("Error in "+dlModule+": ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)

# set params and run manually in following downloaders
# downloader_day
# downloader_dtp
# downloader_gaz_po_ukr
# downloader_journal_krajina
# downloader_molbuk
# downloader_tyzhden
# downloader_umoloda

#================= main call =======================
logging.basicConfig(filename='downloader.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')
mode1()
