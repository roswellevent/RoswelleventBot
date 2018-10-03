import configparser
import platform
import os


class BotConfig():

    def __init__(self):
        if platform.system() == 'Windows':
            self.__CONFIG_FILE ='C:\\Users\\roswellevent\\PycharmProjects\\RoswelleventBot-Git\\config.ini'
        else:
            self.__CONFIG_FILE = '/home/pi/scripts/config.ini'
        if os.path.exists(self.__CONFIG_FILE):
            self.config = self.readConfigFile()
        else:
            raise Exception('{} Not Found'.format(self.__CONFIG_FILE ))

    def readConfigFile(self):
        config = configparser.ConfigParser()
        config.read(self.__CONFIG_FILE)
        return config

    def getTelegramBotToken(self):
        return self.config['telegram']['BOT_TOKEN']

    def getMyTelegramID(self):
        return self.config['telegram']['ROSWELLEVENT_ID']


    def getStockNo(self):
        stock_no = self.config['stock']['stock_no'].split(',') # type:list
        stock_set = set(list(map(int, stock_no)))
        return stock_set

    def addStockNo(self, m_stock_no):
        stock_set = self.getStockNo(self.config)
        stock_set.add(m_stock_no)
        self.writeConfigFile(self.config,stock_set)

    def removeStockNo(self, m_stock_no):
        stock_set = self.getStockNo(self.config)
        if m_stock_no in stock_set:
            stock_set.remove(m_stock_no)
            self.writeConfigFile(self.config,stock_set)
            return True
        else:
            return False

    def writeConfigFile(self,m_stock_set):
        self.self.config['stock']['stock_no'] = ','.join(map(str,sorted(m_stock_set)))
        with open(self.__CONFIG_FILE,'w+') as f:
            self.config.write(f)


