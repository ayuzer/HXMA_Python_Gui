# # System imports
# import os

# # App imports
# from settings import BASE_PATH
# from settings import APP_NAME
# from settings import ENABLE_ERROR_DECORATOR

from core import VAR

ERROR_MESSAGES = []

class KEY(object):
    SERV = '__server_address__'
    HOST = 'host'
    PORT = 'port'

class ServMixin(object):
    """
    This is a mixin??(I think this is the correct usage) which allows the main program
     to save and load server addresses/ports which are saved in settings

     I doubt this will work as we dont load variables or monitor in here
    """
    def set_server_address(self):
        key = self.__class__.__name__

        try:
            server_settings = self.settings.get(key)
            serv_dict = server_settings.get(KEY.SERV)

            print "SETTING SERVER ADDRESS %s TO %s" % (key, serv_dict)

            self.monitor.update(VAR.SERVER_HOST, serv_dict[KEY.HOST])
            self.monitor.update(VAR.SERVER_PORT, serv_dict[KEY.PORT])
            self.monitor.update(VAR.SERVER_ADDRESS,''.join((serv_dict[KEY.HOST],':',serv_dict[KEY.PORT])))
            return True
        except:
            return False
    def save_server_address(self):

        key = self.__class__.__name__

        serv_dict = {
            KEY.HOST : self.monitor.get_value(VAR.SERVER_HOST),
            KEY.PORT : self.monitor.get_value(VAR.SERVER_PORT),
        }

        print "SAVING SERVER ADDRESS %s TO %s" % (key, serv_dict)

        server_settings = self.settings.get(key, {})
        server_settings[KEY.SERV] = serv_dict
        self.settings[key] = server_settings
