


import jaydebeapi
from decimal import *
import time
import datetime
from datetime import date
from datetime import time
from datetime import datetime  
import locale,os
import platform
from datetime import datetime, timedelta


# In[4]:


def Informixdriver():
    if platform.system() == "Windows": 
        driver1="C:\\SigLifeReporting_Informix\\jdbc-4.50.4.1.jar"
        driver2="C:\\SigLifeReporting_Informix\\bson-4.2.0.jar"        
    else:
        #Linux
        driver1="/jdbc-4.50.4.1.jar"
        driver2="/bson-4.2.0.jar"

    return driver1,driver2


# In[5]:


def MSdriver():
    if platform.system() == "Windows":
        locale.setlocale(locale.LC_ALL, '')          
        pth="C:\\SigLifeReporting_Informix\\UCanAccess\\"
        pth1="C:\\SigLifeReporting_Informix\\UCanAccess\\lib\\"
    else:
        #Linux
        pth="/UCanAccess/"
        pth1=pth+"lib/"            
                    
    # Driveri za MS-Access: https://ucanaccess.sourceforge.net/site.html            
    ucanaccess_jars = [
        pth+"ucanaccess-5.0.1.jar",
        pth1+"commons-lang3-3.8.1.jar",
        pth1+"commons-logging-1.2.jar",
        pth1+"hsqldb-2.5.0.jar",
        pth1+"jackcess-3.0.1.jar",
    ]

    if platform.system() == "Windows":    
        classpath = ";".join(ucanaccess_jars)
    else:
        classpath = ":".join(ucanaccess_jars)        
    return classpath 


# In[6]:


import jaydebeapi
    
def OSISinit():
    
    OK=True
    user="appuser"
    password="OxBm?Q(*"
    
    driver1,driver2=Informixdriver()
    driver3=MSdriver()
    
    try:        
        conn = jaydebeapi.connect("com.informix.jdbc.IfxDriver",
                                  "jdbc:informix-sqli://192.168.100.120:5864/uniqa_live:DB_LOCALE=en_US.utf8",
                                  [user, password],
                                  [driver1,driver2,driver3])
        print ("conn",conn)
        db=conn.cursor()
    except Exception as e:
        print ("Error: ",e)
        return "",False                    

    return db,OK

    








