import MySQLdb
import math
from numpy import arange,array,ones,linalg
import numpy as np
from pylab import plot,show
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from datetime import date, timedelta
conn = MySQLdb.connect (host = "localhost",user = "root", passwd = "", db = "heatsolc")
cursor = conn.cursor (MySQLdb.cursors.DictCursor)

def getVesselData(chpId):
  d = {}
  # query = "delete from dht_trans"
  # cursor.execute(query)
  # query = "insert into dht_trans select * from dht_trans where chp_id ='"+str(chpId)+"'"
  # cursor.execute(query)
  # print ' chp_id dht_id and ', chpId , ' ', dht_id
  query = "select vm.vess_name, vm.vess_id, ch.voy_no, ch.total_grade from vessel_master vm, chp_head ch where ch.vess_id = vm.vess_id and ch.chp_id = '"+str(chpId)+"'"
  cursor.execute(query)
  row = cursor.fetchone()
  d['chp_id']              =  chpId
  d['vess_name']  =   row['vess_name']
  d['vess_id']   = row['vess_id']
  d['voy_no']      =  row['voy_no']
  d['total_grade']    =  row['total_grade']
  # d['dht_id'] = dht_id
  try:
    query = "select dm.NumOfTanks from dimensionmaster dm,where vess_id='"+str(d['vess_id'])+"'"
    cursor.execute (query)
    row = cursor.fetchone()
    d['tank_system']                      =   row[0]/2
  except:
    d['tank_system'] = 7

  if(d['tank_system'] == 0): 
    d['tank_system'] = 7

  # qry ="select sw_temp, air_temp, wind_force, rel_wind_dir, temp_type, dht_id from dht_head dh where dh.chp_id ='"+str(chpId)+"' and dht_id ='"+str(dht_id)+"'"
  # cursor.execute (qry)
  # row = cursor.fetchone() 
  # d['air_temp']                         =   row['air_temp']
  # d['sea_temp']                         =   row['sw_temp']
  return d

def getGradeData(chpId, dht):
  dt = []
  try:
    #print 'inside try'
    qry ="select ct.id, ct.chp_id, ct.voy_no, ct.grade_no,ct.cargo_grade_name, ct.loading_port, ct.etb_load_port, ct.etd_load_port, ct.discharge_port, ct.eta_discharge_port, ct.etd_discharge_port,ct.loden_leg_dist,sum(dt.qty),ct.api_sp_gravity,ct.pour_point,ct.cloud_point,ct.ext_load_temp,ct.temp_during_transit,ct.temp_dispatch_port, ct.status from dht_trans dt, chp_trans ct where ct.chp_id='"+str(chpId)+"' and ct.chp_id = dt.chp_id and dt.dht_id = '"+str(dht)+"' and ct.grade_no =  dt.cargo_grade group by grade_no"
    cursor.execute (qry)
    # row = cursor.fetchall()
    # t_g =  len(row)
    row  =  cursor.fetchone()
    #print 'rowssss', row
    grade_data = row

   # print 'dht in grade data', dht
    #print grade_data[0]
    #print grade_data[1]
    #print row

    while row != None:
    #  print 'in while'
      d = {}
      d['chp_id'] =  row['chp_id']
      d['voy_no'] =   row['voy_no']
      d['grade_no']  =   row['grade_no']
      d['cargo_grade_name']  =  row['cargo_grade_name']
      d['dht_id'] =  dht
      d['chp_id'] = chpId
     # d['t_g'] =  t_g

      '''
      d['loading_port']       =   row[5]
      d['etb_load_port']       =   row[6]
      d['etd_load_port']         =   row[7]
      d['discharge_port']              =   row[8]
      d['eta_discharge_port']          =   row[9]
      d['etd_discharge_port']          =   row[10]
      d['loden_leg_dist']              =   row[11]
      '''
      d['qty']                         =   row['sum(dt.qty)']
      d['api_sp_gravity']              =   row['api_sp_gravity']
      #print 'api sp gr', row[13]  
      '''
      d['pour_point']                  =   row[14]
      d['cloud_point']                 =   row[15]
      d['ext_load_temp']               =   row[16]
      d['temp_during_transit']         =   row[17]
      d['temp_dispatch_port']          =   row[18]
      '''
      #print 'beforedddd', d
      #print d
      #print 'string api_sp_gravity is ', d['api_sp_gravity']
      if(float(d['api_sp_gravity']) > 1.2):
          d['api_sp_gravity']     =    141.5/(131.5 + float(d['api_sp_gravity']))
      
      if(float(d['api_sp_gravity']) < 0.7):
          d['api_sp_gravity']     =    141.5/(131.5 + float(d['api_sp_gravity']))
      

      dt.append(d)
      #print 'afterdddd' , d
      #print 'dtttt is' , dt
      row =  cursor.fetchone()

  except:
    pass
  #print 'dtttt', dt
  return dt
def getNextDayTanksTemp(vess, grade, dhtn, temp_type):
  avgTemp = 0
  count = 0
  dt = [[],[]]
  #next_day_temp =[[],[]]
  #print 'tank_sys', vess['tank_system']
  #print 'nextday dht is',dhtn
 # print 'next day grade is', grade
  q1 = "select count(tank) from dht_trans where chp_id = '"+str(vess['chp_id'])+"' and dht_id  = '"+str(dhtn)+"'"
  q2  ="select count(distinct(tank)) from dht_trans where chp_id = '"+str(vess['chp_id'])+"' and dht_id  = '"+str(dhtn)+"'"

  cursor.execute (q1)
  row1 = cursor.fetchone()

  cursor.execute (q2)
  row2 = cursor.fetchone()

  if(row1['count(tank)']!=row2['count(distinct(tank))']):
    return [[],[]]

  for i in range(0, 2):

    for j in range(0, vess['tank_system']):
      d = {}
      ndt = {}
      if(i==0):
        p_s = 'P'
      else:
        p_s = 'S'
      d['name'] = str(j+1)+p_s

      try:
        query = "select qty, tank,cargo_grade, cargo_grade_name, avg_temp, rt_top ,rt_medium ,rt_bottom , mt_top,mt_medium ,mt_bottom  from dht_trans where chp_id='"+str(vess['chp_id'])+"' and dht_id='"+str(dhtn)+"' and tank='"+d['name']+"'"       
        cursor.execute (query)
        row = cursor.fetchone()
      #  print 'rowavg', row
        d['quantity'] = row['qty']
        d['cargo_id'] = row['cargo_grade']
        d['cargo_grade_name'] = row['cargo_grade_name']
        d['avg_temp'] = row['avg_temp']
        ndt['avg_temp'] = row['avg_temp']
        d['rt_top']  = row['rt_top']
        d['rt_medium'] =  row['rt_medium']
        d['rt_bottom'] = row['rt_bottom']
        d['mt_top'] =  row['mt_top']
        d['mt_medium']  = row['mt_medium']
        d['mt_bottom'] =  row['mt_bottom']
        d['heatloss_cond'] = 0
        d['heatloss_rad'] = 0

        if(temp_type=='F'):
          print ' before temp type is F' , d
          d['avg_temp'] = (d['avg_temp']-32)*5/9 
          ndt['avg_temp'] = (row['avg_temp']-32)*5/9
          d['rt_top']  = (row['rt_top']-32)*5/9
          d['rt_medium'] =  (row['rt_medium']-32)*5/9
          d['rt_bottom'] = (row['rt_bottom']-32)*5/9
          d['mt_top'] =  (row['mt_top']-32)*5/9
          d['mt_medium']  = (row['mt_medium']-32)*5/9
          d['mt_bottom'] =  (row['mt_bottom']-32)*5/9
          print 'after converting temp_type to C', d

      except:
        pass

      dt[i].append(d)
 # print 'next day temp is' 
  return dt
def getTankData(vess, grade, dhtn, air_temp, sea_temp, temp_type):
#  print 'dht_id', vess['dht_id'
  avgTemp = 0
  non_zero_tank = 0
  count = 0
  dt = [[],[]]
  next_day_temp =[[],[]]

  #print 'tank_sys', vess['tank_system']

  q1 = "select count(tank) from dht_trans where chp_id = '"+str(vess['chp_id'])+"' and dht_id  = '"+str(dhtn)+"'"
  q2  ="select count(distinct(tank)) from dht_trans where chp_id = '"+str(vess['chp_id'])+"' and dht_id  = '"+str(dhtn)+"'"

  cursor.execute (q1)
  row1 = cursor.fetchone()

  cursor.execute (q2)
  row2 = cursor.fetchone()

  if(row1['count(tank)']!=row2['count(distinct(tank))']):
    return [[],[]]


  for i in range(0, 2):

    for j in range(0, vess['tank_system']):
      
      d = {}
      ndt = {}
      if(i==0):
        p_s = 'P'
      else:
        p_s = 'S'
      d['name'] = str(j+1)+p_s

      try:
        query = "select qty, tank,cargo_grade, cargo_grade_name, avg_temp, rt_top ,rt_medium ,rt_bottom , mt_top,mt_medium ,mt_bottom  from dht_trans where chp_id='"+str(vess['chp_id'])+"' and dht_id='"+str(dhtn)+"' and tank='"+d['name']+"'"       
        cursor.execute (query)
        row = cursor.fetchone()
        #print 'rowavg', row
        d['quantity'] = row['qty']
        d['cargo_id'] = row['cargo_grade']
        d['cargo_grade_name'] = row['cargo_grade_name']
        d['avg_temp'] = row['avg_temp']
        ndt['avg_temp'] = row['avg_temp']
        d['rt_top']  = row['rt_top']
        d['rt_medium'] =  row['rt_medium']
        d['rt_bottom'] = row['rt_bottom']
        d['mt_top'] =  row['mt_top']
        d['mt_medium']  = row['mt_medium']
        d['mt_bottom'] =  row['mt_bottom']
        d['heatloss_cond'] = 0
        d['heatloss_rad'] = 0

        

        if(temp_type=='F'):
          print ' before temp type is F' , d
          d['avg_temp'] = (d['avg_temp']-32)*5/9 
          ndt['avg_temp'] = (row['avg_temp']-32)*5/9
          d['rt_top']  = (row['rt_top']-32)*5/9
          d['rt_medium'] =  (row['rt_medium']-32)*5/9
          d['rt_bottom'] = (row['rt_bottom']-32)*5/9
          d['mt_top'] =  (row['mt_top']-32)*5/9
          d['mt_medium']  = (row['mt_medium']-32)*5/9
          d['mt_bottom'] =  (row['mt_bottom']-32)*5/9

        #  print 'after converting temp_type to C', d

        if(float(d['quantity']) >0 and d['cargo_id']):
          avgTemp = avgTemp + float(d['avg_temp'])
          count += 1
        dt[i].append(d)  
        
        #print 'dtd', dt
      except:
        pass

 # print 'next day temp is' 

  # for i in range(0, 2):
  #   for j in range(0, vess['tank_system']):

  #     d = {}
  #     #ndt = {}
  #     p_s =''
  #     if(i==0):
  #       p_s = 'P'
  #     else:
  #       p_s = 'S'
  #     d['name'] = str(j+1)+p_s

  #     # #try:
  #     # query = "select qty, cargo_grade, cargo_grade_name, avg_temp  from dht_trans where chp_id='"+str(vess['chp_id'])+"' and dht_id='"+str(dhtn)+"' and tank='"+d['name']+"'" 
  #     # cursor.execute (query)
  #     # rowc = cursor.fetchone()

  #     try:
  #       query = "select qty, tank,cargo_grade, cargo_grade_name, avg_temp, rt_top ,rt_medium ,rt_bottom , mt_top,mt_medium ,mt_bottom  from dht_trans where chp_id='"+str(vess['chp_id'])+"' and dht_id='"+str(dhtn)+"' and tank='"+d['name']+"'"       
  #       cursor.execute (query)
  #       row = cursor.fetchone()
  #     #  print 'rowavg', row
  #       d['quantity'] = row['qty']
  #       d['cargo_id'] = row['cargo_grade']
  #       d['cargo_grade_name'] = row['cargo_grade_name']
  #       d['avg_temp'] = row['avg_temp']
  #      # ndt['avg_temp'] = row['avg_temp']
  #       d['rt_top']  = row['rt_top']
  #       d['rt_medium'] =  row['rt_medium']
  #       d['rt_bottom'] = row['rt_bottom']
  #       d['mt_top'] =  row['mt_top']
  #       d['mt_medium']  = row['mt_medium']
  #       d['mt_bottom'] =  row['mt_bottom']
  #       d['heatloss_cond'] = 0
  #       d['heatloss_rad'] = 0

  #       if(temp_type=='F'):
  #         print ' before temp type is F' , d
  #         d['avg_temp'] = (d['avg_temp']-32)*5/9 
  #         ndt['avg_temp'] = (row['avg_temp']-32)*5/9
  #         d['rt_top']  = (row['rt_top']-32)*5/9
  #         d['rt_medium'] =  (row['rt_medium']-32)*5/9
  #         d['rt_bottom'] = (row['rt_bottom']-32)*5/9
  #         d['mt_top'] =  (row['mt_top']-32)*5/9
  #         d['mt_medium']  = (row['mt_medium']-32)*5/9
  #         d['mt_bottom'] =  (row['mt_bottom']-32)*5/9
  #         print 'after converting temp_type to C', d

  #       if(d[i][j]['quantity'] >0 and d[i][j]['cargo_id']):
  #         avgTemp = avgTemp + d[i][j]['avg_temp']
  #         count += 1
  #       dt[i].append(d)

      
  #     except:
  #       print 'error in get tank data  and dhtid and chpid is', dhtn, ' ', vess['chp_id'], d['name']
  #       pass

      # if(float(rowc[3]) > float(rowp[3])):
        #print 
     #   print 'current dht_id is', vess['dht_id'], 'next dht-id', dhtn
        #print 'rowc0 ', rowc[0], 'rowp0', rowp[0]
       # print 'avgtc',rowc[3] , 'and ', 'avgtp', rowp[3] 
        #print 'inside rowc', rowc  
       
       # ndt['avg_temp'] = rowc[3]
  
       #non_zero_tank+=1
       #print 'cargo id is', d['cargo_id']
     
  if(count > 0):
    avgTemp = avgTemp/float(count) 
  #print 'no of noze zero tanks are', non_zero_tank

  flag = 0
  query = "select L,H,W from dimensiontrans where vess_id='"+str(vess['vess_id'])+"' order by RecID"
  cursor.execute (query)
  for j in range(0, vess['tank_system']):
  ##  print 'inside tank_system', j
    for i in range(0,2):
      row = cursor.fetchone()
      try:
        #  print 'llllll', row[0]
        dt[i][j].update({'L':row['L']})       
        dt[i][j].update({'W':row['W']})
        dt[i][j].update({'H':row['H']})
        #print 'lwh', dt[i][j]['L']
       # print 'after except'
        if(dt[i][j]['cargo_id'] > 0 and dt[i][j]['quantity'] > 0):
          #print 'innnnn'
         # print 'apip'
          dt[i][j].update({'api_sp_gravity':grade[dt[i][j]['cargo_id'] - 1]['api_sp_gravity']})
          ##print 'apip'
         # print grade[dt[i][j]['cargo_id'] - 1]['api_sp_gravity']
         # print 'aaaaappppiiiiii', dt[i][j]['api_sp_gravity']
          
          try:
            if(float(dt[i][j]['api_sp_gravity']) > 1.2):
              dt[i][j]['api_sp_gravity']     =    141.5/(131.5 + float(dt[i][j]['api_sp_gravity']))
            if(float(dt[i][j]['api_sp_gravity']) < 0.7):
              dt[i][j]['api_sp_gravity']     =    141.5/(131.5 + float(dt[i][j]['api_sp_gravity']))

          except:
              dt[i][j]['api_sp_gravity']     =    0.9
          dt[i][j].update({'sounding':float(dt[i][j]['quantity'])/(float(dt[i][j]['L'])*float(dt[i][j]['W'])*float(dt[i][j]['api_sp_gravity']))})
          dt[i][j].update({'ullage':float(dt[i][j]['H']) - float(dt[i][j]['sounding'])})
          dt[i][j].update({'air_temp': (dt[i][j]['sounding'] * float(dt[i][j]['avg_temp']) + dt[i][j]['ullage']*float(air_temp))/float(dt[i][j]['H'])})    
          #print 'before print'
         # print 'tank i, j air temp', i, j, 'name is', dt[i][j]['name'], 'air temp is', dt[i][j]['air_temp'] , 'avg_temp', dt[i][j]['avg_temp'],'ullage is',dt[i][j]['ullage'], 'sounding' ,dt[i][j]['sounding']
          if(dt[i][j]['ullage'] <0):
            flag =1
            # print 'oops ! ullage is negative '
            # print 'check in soudning', 'qty iss', dt[i][j]['quantity'], 'L, W, H is ', dt[i][j]['L'], ' ', dt[i][j]['W'], ' ',  dt[i][j]['H']
            # print 'api sp gravity is', dt[i][j]['api_sp_gravity']

          dt[i][j].update({'sh':((float(dt[i][j]['avg_temp']) + 32) * 1.8 + 671) * (2.1- float(dt[i][j]['api_sp_gravity']))/2030 * 1/0.2388})
          dt[i][j].update({'bottom_temp':0.5 * float(dt[i][j]['avg_temp']) + 0.5*float(sea_temp)}) 
        else:
          dt[i][j]['api_sp_gravity']         =    0
          dt[i][j]['air_temp']               =    0.85 * avgTemp + 0.15 * air_temp
          dt[i][j]['bottom_temp']            =    0
          dt[i][j]['sounding']               =    0
          dt[i][j]['ullage']                 =    dt[i][j]['H']
          dt[i][j]['sh']                     =    0    
        #print 'sounding inside gettank is ',  dt[i][j]['sounding'] 
      except:

        pass    
   # print dt
  if(flag):
    return [[],[]]
  else:
    return dt    

def calcGradeTemp(tank, grade, vess):
  #try:
 # print 
  for k in range(1, vess['total_grade']+1):
    avgTemp =0 
    qty =  0
    for i in range(0, 2):
      for j in range(0, vess['tank_system']):
        if(tank[i][j]['cargo_id']==k):
          avgTemp +=float(tank[i][j]['avg_temp'])*float(tank[i][j]['quantity'])
          qty+=float(tank[i][j]['quantity'])
   # print 'inside calcGradeTemp', k-1 
    if(qty>0):
      avgTemp =avgTemp/float(qty)
      grade[k-1].update({'temp':avgTemp})
    #  print 'avg temp of grade ', k, ' is', grade[k-1]['temp']
     # print 'grade k is ', grade[k-1
  #except:
  #  pass
  

def calcHeatFlowTank(tank, grade, vess,tank_next, tname, air_temp, sea_temp):

  print '-------------------------------------------------------'
  #---contribution due to consuction ----------------_##
  port=0.0 
  starboard=0.0 
  top=0.0 
  bottom=0.0 
  front=0.0 
  back=0.0

  #----contribution due to radiation from all faces--------#
  port1=0.0 
  starboard1=0.0 
  top1=0.0 
  bottom1=0.0 
  front1=0.0 
  back1=0.0
  x1= -1
  x2 = -1
  y = 0
  flag = 0
  flago = 0

  #print 'tank  data is', tank
  #heat_loss_tank[0].append(vess['dht_id'])
  for i in range(0, 2):
   # print 'vess tank system is', vess['tank_system']
    for j in range(0, vess['tank_system']):
     # print 'i, j', i,j, 'qty is', tank[i][j]['quantity'], 'cargo id is ', tank[i][j]['cargo_id']
      try:
        if(float(tank[i][j]['quantity'])>0 and float(tank[i][j]['cargo_id'])>0):
        #  print 'tank i j', tank[i][j]['name'] , 'and passed tank', tname
          if(tank[i][j]['name'] == tname):
            print 'compare'
            print 'qty is', tank[i][j]['quantity'] , 'avg temp is', tank[i][j]['avg_temp'] 
            flag =1
            #try:
            if(i==0):
             # print 'in i=0'
              t_amb  = 0.7 * float(sea_temp) +0.3*float(tank[i][j]['avg_temp'])
            #  print 'tamb ',t_amb
             # print 'l', tank[i][j]['L'] ,'sounding', tank[i][j]['sounding'], 'avg_temp', tank[i][j]['avg_temp']
              port = float(tank[i][j]['L']) * float(tank[i][j]['sounding']) * (float(tank[i][j]['avg_temp'])-t_amb)
              port = port + float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-t_amb)
              
              port1 = float(tank[i][j]['L']) * float(tank[i][j]['sounding']) * (math.pow(float(tank[i][j]['avg_temp']), 4)-math.pow(t_amb,4)) 
              port1 = port1 + float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(t_amb,4))
           #   print 'port 1 is ', port1
              if(tank[i][j]['sounding']>tank[i+1][j]['sounding']):
                
                starboard=float(tank[i][j]['L'])*float(tank[i+1][j]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i+1][j]['avg_temp']))
                starboard = starboard + float(tank[i][j]['L'])*(float(tank[i][j]['sounding'])-float(tank[i+1][j]['sounding']))*(float(tank[i][j]['avg_temp'])-float(tank[i+1][j]['air_temp']))
                starboard = starboard + float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i+1][j]['air_temp']))
               
                starboard1=float(tank[i][j]['L'])*float(tank[i+1][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i+1][j]['avg_temp']),4))
                starboard1 = starboard1 + float(tank[i][j]['L'])*(float(tank[i][j]['sounding'])-float(tank[i+1][j]['sounding']))*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i+1][j]['air_temp']),4))
                starboard1 = starboard1 + float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i+1][j]['air_temp']),4))
                         
              else:
                starboard=float(tank[i][j]['L'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i+1][j]['avg_temp']))
                starboard = starboard + float(tank[i][j]['L'])*(float(tank[i+1][j]['sounding'])-float(tank[i][j]['sounding']))*(float(tank[i][j]['air_temp'])-float(tank[i+1][j]['avg_temp']))
                starboard = starboard + float(tank[i][j]['L'])*float(tank[i+1][j]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i+1][j]['air_temp']))

                starboard1=float(tank[i][j]['L'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i+1][j]['avg_temp']),4))
                starboard1 = starboard1 + float(tank[i][j]['L'])*(float(tank[i+1][j]['sounding'])-float(tank[i][j]['sounding']))*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i+1][j]['avg_temp']),4))
                starboard1 = starboard1 + float(tank[i][j]['L'])*float(tank[i+1][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i+1][j]['air_temp']),4))

            if(i==1):
              t_amb = 0.7*float(sea_temp)+0.3*float(tank[i][j]['avg_temp'])
              starboard=float(tank[i][j]['L'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-t_amb)
              starboard+=float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-t_amb)

              starboard1=float(tank[i][j]['L'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(t_amb,4))
              starboard1+=float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(t_amb,4))
              if(tank[i][j]['sounding']>tank[i-1][j]['sounding']):
                port = float(tank[i][j]['L'])*float(tank[i-1][j]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i-1][j]['avg_temp']))
                port = port + float(tank[i][j]['L'])*(float(tank[i][j]['sounding'])-float(tank[i-1][j]['sounding']))*(float(tank[i][j]['avg_temp'])-float(tank[i-1][j]['air_temp']))
                port = port + float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i-1][j]['air_temp']))

                port1 = float(tank[i][j]['L'])*float(tank[i-1][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i-1][j]['avg_temp']),4))
                port1 = port1 + float(tank[i][j]['L'])*(float(tank[i][j]['sounding'])-float(tank[i-1][j]['sounding']))*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i-1][j]['air_temp']),4))
                port1 = port1 + float(tank[i][j]['L'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i-1][j]['air_temp']),4))

              else:
                port = float(tank[i][j]['L'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i-1][j]['avg_temp']))
                port = port + float(tank[i][j]['L'])*(float(tank[i-1][j]['sounding'])-float(tank[i][j]['sounding']))*(float(tank[i][j]['air_temp'])-float(tank[i-1][j]['avg_temp']))
                port = port + float(tank[i][j]['L'])*float(tank[i-1][j]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i-1][j]['air_temp']))

                port1 = float(tank[i][j]['L'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i-1][j]['avg_temp']),4))
                port1 = port1 + float(tank[i][j]['L'])*(float(tank[i-1][j]['sounding'])-float(tank[i][j]['sounding']))*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i-1][j]['avg_temp']),4))
                port1 = port1 + float(tank[i][j]['L'])*float(tank[i-1][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i-1][j]['air_temp']),4))

          #------------------------caluclaint heat flow from tank front and back side-------#
            if(j==0):
              t_amb = 0.3*float(tank[i][j]['avg_temp'])+0.7*float(sea_temp)
              front=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-t_amb)
              front = front + float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-t_amb)

              front1=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(t_amb,4))
              front1 = front1 + float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(t_amb,4))

            else:
              if(tank[i][j]['sounding']>tank[i][j-1]['sounding']):
                front=float(tank[i][j]['W'])*float(tank[i][j-1]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i][j-1]['avg_temp']))
                front+=float(tank[i][j]['W'])*(float(tank[i][j]['sounding'])-float(tank[i][j-1]['sounding']))*(float(tank[i][j]['avg_temp'])-float(tank[i][j-1]['air_temp']))
                front+=float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i][j-1]['air_temp']))
              
                front1=float(tank[i][j]['W'])*float(tank[i][j-1]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j-1]['avg_temp']),4))
                front1+=float(tank[i][j]['W'])*(float(tank[i][j]['sounding'])-float(tank[i][j-1]['sounding']))*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j-1]['air_temp']),4))
                front1+=float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i][j-1]['air_temp']),4))

              else:
                front=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i][j-1]['avg_temp']))
                front = front + float(tank[i][j]['W'])*(float(tank[i][j-1]['sounding'])-float(tank[i][j]['sounding']))*(float(tank[i][j]['air_temp'])-float(tank[i][j-1]['avg_temp']))
                front = front + float(tank[i][j]['W'])*float(tank[i][j-1]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i][j-1]['air_temp']))

                front1=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j-1]['avg_temp']),4))
                front1 = front1 + float(tank[i][j]['W'])*(float(tank[i][j-1]['sounding'])-float(tank[i][j]['sounding']))*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i][j-1]['avg_temp']),4))
                front1 = front1 + float(tank[i][j]['W'])*float(tank[i][j-1]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i][j-1]['air_temp']),4))

            if(j==vess['tank_system']-1):
              t_amb = 0.3*float(tank[i][j]['avg_temp'])+0.7*float(sea_temp)        
              back=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-t_amb)
              back = back + float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-t_amb)

              back1=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(t_amb,4))
              back1 = back1 + float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(t_amb,4))

            else:
              #print 'inside keyerror souning', tank[i][j]['sounding'] , 'i and j is', i, j ,' ', tank[i][j+1]['sounding']
              if(float(tank[i][j]['sounding'])>float(tank[i][j+1]['sounding'])):
                back=float(tank[i][j]['W'])*float(tank[i][j+1]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i][j+1]['avg_temp']))
                back = back + float(tank[i][j]['W'])*(float(tank[i][j]['sounding'])-float(tank[i][j+1]['sounding']))*(float(tank[i][j]['avg_temp'])-float(tank[i][j+1]['air_temp']))
                back = back + float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i][j+1]['air_temp']))

                back1=float(tank[i][j]['W'])*float(tank[i][j+1]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j+1]['avg_temp']),4))
                back1 = back1 + float(tank[i][j]['W'])*(float(tank[i][j]['sounding'])-float(tank[i][j+1]['sounding']))*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j+1]['air_temp']),4))
                back1 = back1 + float(tank[i][j]['W'])*float(tank[i][j]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i][j+1]['air_temp']),4))


              else:
                back=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(float(tank[i][j]['avg_temp'])-float(tank[i][j+1]['avg_temp']))
                back = back + float(tank[i][j]['W'])*(float(tank[i][j+1]['sounding'])-float(tank[i][j]['sounding']))*(float(tank[i][j]['air_temp'])-float(tank[i][j+1]['avg_temp']))
                back = back + float(tank[i][j]['W'])*float(tank[i][j+1]['ullage'])*(float(tank[i][j]['air_temp'])-float(tank[i][j+1]['air_temp']))

                back1=float(tank[i][j]['W'])*float(tank[i][j]['sounding'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j+1]['avg_temp']),4))
                back1 = back1 + float(tank[i][j]['W'])*(float(tank[i][j+1]['sounding'])-float(tank[i][j]['sounding']))*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i][j+1]['avg_temp']),4))
                back1 = back1 + float(tank[i][j]['W'])*float(tank[i][j+1]['ullage'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(tank[i][j+1]['air_temp']),4))

            d= {}

            top=float(tank[i][j]['L'])*float(tank[i][j]['W'])*(float(tank[i][j]['air_temp'])-float(air_temp))
            bottom=float(tank[i][j]['L'])*float(tank[i][j]['W'])*(float(tank[i][j]['avg_temp'])-float(tank[i][j]['bottom_temp']))

            top1=float(tank[i][j]['L'])*float(tank[i][j]['W'])*(math.pow(float(tank[i][j]['air_temp']),4)-math.pow(float(air_temp),4))
            bottom1=float(tank[i][j]['L'])*float(tank[i][j]['W'])*(math.pow(float(tank[i][j]['avg_temp']),4)-math.pow(float(tank[i][j]['bottom_temp']),4))

            #print 'tank i j is', i,j, 'name is', tank[i][j]['name']
            #print 'qty is', tank[i][j]['quantity'] , 'avg temp is', tank[i][j]['avg_temp']
            #tank[i][j]['heatloss_cond']= (port + starboard + top + bottom + front + back)
            #tank[i][j]['heatloss_rad']= (port1 + starboard1 + top1 + bottom1 + front1 + back1)
           # d['tank'] = tank[i][j]['name']
           # d['heatloss'] = float(tank[i][j]['heatloss'])
            #print 'tank name ', tank[i][j]['name'], 'quantity', tank[i][j]['quantity'], 'cargo id ', tank[i][j]['cargo_id'], 'prev day temp ', tank_data[i][j]['avg_temp'], 'next day temp is', tank_next[i][j]['avg_temp'], 'api sp heat', tank_data[i][j]['sh']
            if(float(tank_next[i][j]['avg_temp'])>0):
              y = float(tank[i][j]['quantity'])*float(tank[i][j]['sh'])*(float(tank_next[i][j]['avg_temp'])-float(tank[i][j]['avg_temp']))
              print 'and heat loss from', i, j, tank[i][j]['name'], 'due to temp drop', y
              if(y<0):
                 x1 =  (port + starboard + top + bottom + front + back)
                 x2 =  (port1 + starboard1 + top1 + bottom1 + front1 + back1)

              else:
                x1 = -1
                x2 = -1
                y =   -1
                  #yy.append(heat_temp_drop)
             #   print 'heat loss tank i and j is ', i, j , tank[i][j]['heatloss']
                #heat_loss_tank.append(tank[i][j]['heatloss'])
             # except:
              #  pass
            if(flag):
              flago =  1
              break  
      except:
        pass 
    if(flago):
      break

           
  return x1 ,x2 ,y  

#--------------------regression for multiple level ---------------#

def get_data_class(dwt1, dwt2, t1, t2, wf1, wf2, s1, s2):

  # qry = " select dt.chp_id, dh.dht_id, dh.vess_id, dh.voy_no, dm.NumOfTanks, dm.DWT, "+\
  # "dt.tank, dt.avg_temp, dt.qty, dt.cargo_grade, dt.rt_top, dt.rt_medium, dt.rt_bottom , "+\
  # " dt.mt_top, dt.mt_medium, dt.mt_bottom, dh.cargo_heating_total_fo, dh.sw_temp, dh.air_temp, dh.wind_force, dh.rel_wind_dir, "+\
  # " dh.deck_wetness, dh.temp_type, dt.cargo_grade_name, ch.total_grade , ct.grade_no, ct.api_sp_gravity, ct.pour_point, ct.cloud_point "+\
  # " from dht_trans dt, dht_head dh, chp_head ch , chp_trans ct , dimensionmaster dm "+\
  # " where dt.chp_id = ch.chp_id and dh.chp_id = ch.chp_id and ch.chp_id = ct.chp_id "+\
  # " and dh.dht_id = dt.dht_id and dm.vess_id = ch.vess_id and dt.cargo_grade =  ct.grade_no and (dm.DWT >= '"+str(dwt1)+"' and dm.DWT<'"+str(dwt2)+"') and "+\
  # " ((dh.temp_type='F' and (((dt.avg_temp-32)*5/9 -(dh.air_temp+dh.sw_temp)/2)>='"+str(t1)+"' and ((dt.avg_temp-32)*5/9 -(dh.air_temp+dh.sw_temp)/2)<'"+str(t2)+"')) "+\
  # " OR (dh.temp_type='C' and (((dt.avg_temp-(dh.air_temp+dh.sw_temp)/2)>= '"+str(t1)+"' and ((dt.avg_temp-(dh.air_temp+dh.sw_temp)/2)<'"+str(t2)+"'))) "+\
  # " and (dh.wind_force >='"+str(wf1)+"'  and dh.wind_force < '"+str(wf2)+"')" +\
  # " and ((ct.api_sp_gravity> 1.2 and (141.5/(131.5 + ct.api_sp_gravity)>='"+str(s1)+"' and 141.5/(131.5 + ct.api_sp_gravity)<'"+str(s2)+"')) "+\
  # " OR (ct.api_sp_gravity<0.7 and (141.5/(131.5 + ct.api_sp_gravity)>='"+str(s1)+"' and 141.5/(131.5 + ct.api_sp_gravity)<'"+str(s2)+"'))" +\
  # " OR ((ct.api_sp_gravity>=0.7 and ct.api_sp_gravity<1.2) and ct.api_sp_gravity>='"+str(s1)+"' and ct.api_sp_gravity <'"+str(s2)+"')) and dh.bc_cargo_heating='0.0' "
  
  qry = "select dt.chp_id, dh.dht_id, dh.dht_date, dh.vess_id, dh.voy_no, dm.NumOfTanks, dm.DWT, "+\
  "dt.tank, dt.avg_temp, dt.qty, dt.cargo_grade, dt.rt_top, dt.rt_medium, dt.rt_bottom , "+\
  " dt.mt_top, dt.mt_medium, dt.mt_bottom, dh.cargo_heating_total_fo, dh.sw_temp, dh.air_temp, dh.wind_force, dh.rel_wind_dir, "+\
  " dh.deck_wetness, dh.temp_type, dt.cargo_grade_name, ch.total_grade , ct.grade_no, ct.api_sp_gravity, ct.pour_point, ct.cloud_point "+\
  " from dht_trans dt, dht_head dh, chp_head ch , chp_trans ct , dimensionmaster dm "+\
  " where dt.chp_id = ch.chp_id and dh.chp_id = ch.chp_id and ch.chp_id = ct.chp_id "+\
  " and dh.dht_id = dt.dht_id and dm.vess_id = ch.vess_id and dt.cargo_grade =  ct.grade_no and "+\
  "(dm.DWT >= '"+str(dwt1)+"' and dm.DWT<'"+str(dwt2)+"') and "+\
  "((dh.temp_type='F' and ((dt.avg_temp-32)*5/9 -(dh.air_temp+dh.sw_temp)/2)>='"+str(t1)+"' and "+\
  "((dt.avg_temp-32)*5/9 -(dh.air_temp+dh.sw_temp)/2)<'"+str(t2)+"') "+\
  " OR (dh.temp_type='C' and ((dt.avg_temp-(dh.air_temp+dh.sw_temp)/2)>= '"+str(t1)+"' and "+\
  "(dt.avg_temp-(dh.air_temp+dh.sw_temp)/2)<'"+str(t2)+"'))) "+\
  " and (dh.wind_force >='"+str(wf1)+"'  and dh.wind_force < '"+str(wf2)+"')" +\
  " and ((ct.api_sp_gravity> 1.2 and (141.5/(131.5 + ct.api_sp_gravity)>='"+str(s1)+"' and "+\
  "141.5/(131.5 + ct.api_sp_gravity)<'"+str(s2)+"')) "+\
  " OR (ct.api_sp_gravity<0.7 and (141.5/(131.5 + ct.api_sp_gravity)>='"+str(s1)+"' and "+\
  "141.5/(131.5 + ct.api_sp_gravity)<'"+str(s2)+"'))" +\
  " OR ((ct.api_sp_gravity>=0.7 and ct.api_sp_gravity<=1.2) and ct.api_sp_gravity>='"+str(s1)+"' and "+\
  "ct.api_sp_gravity <'"+str(s2)+"')) and dh.bc_cargo_heating='0.0' "
  
  cursor.execute(qry)
  rows =  cursor.fetchall()

  print 'rowssss ', rows
  all_data  = {}
  for row in rows:

    chp_id= row['chp_id']
    if chp_id not in all_data.keys():
      all_data[chp_id] = []

    all_data[chp_id].append({'dht_id':row['dht_id'],'dht_date':row['dht_date'], 'tank': row['tank'],'avg_temp':float(row['avg_temp'])})
    #print all_data
    try:
      a =   row['tank']
      b = a[0]+'COT'+a[1]
      try:

        if(row['temp_type'] =='F'):
          row['avg_temp'] =  (row['avg_temp']-32)*5/9
        if(float(row['api_sp_gravity']) < 0.7):
          #print 'in less that'
        #  print 'api_sp_gravity is before converting', row['api_sp_gravity']
          row['api_sp_gravity']    =    141.5/(131.5 + float(row['api_sp_gravity']))
         # print 'after converting', row['api_sp_gravity'] #

        if(float(row['api_sp_gravity']) > 1.2):
        #  print 'api_sp_gravity is before converting', row['api_sp_gravity']
          row['api_sp_gravity']    =    141.5/(131.5 + float(row['api_sp_gravity']))
         # print 'after converting', row['api_sp_gravity']

      except:
        print 'api sp grvity formatiing problem for chp_id', row['chp_id']
        pass

      try:
        
        q =  "select L, W, H , TankName, vess_id from dimensiontrans where vess_id= '"+str(row['vess_id'])+"' and TankName='"+b+"'"
        cursor.execute(q)
        r =  cursor.fetchone()
        #print r
        row.update({'L': r['L']})
        row.update({'W': r['W']})
        row.update({'H': r['H']})
        row.update({'TankName': r['TankName']})
      #  print 'after updating the row'
       # print row
      except:
        print 'no dimension for vess id ', row['vess_id'] , 'tank', b,  'tankname', r['TankName']
        pass

    except:
      print 
      print 'tank is  name is not gieve in dht_trans for chp_id and vess_id', row['tank'], ' ', row['vess_id']

    #print
  #print '55555'
 # print all_data[5] 
  return all_data 

def get_path_to_class(avg_amb, wf, sg):

  t1=t2=wf1=wf2=s1=s2 = -1
  if(avg_amb<15):

    t1  = -22222
    t2 = 15
    if(wf<4):
      wf1 = -33333
      wf2 = 4
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    elif(wf>=4 and wf<7):
      wf1 = 4
      wf2 = 7

      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80  
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    else:
      wf1 = 7
      wf2 = 33333
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

  elif(avg_amb>=15 and avg_amb<25):
    t1  = 15
    t2 =  25

    if(wf<4):
      wf1 = -33333
      wf2 = 4
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    elif(wf>=4 and wf<7):
      wf1 = 4
      wf2 = 7
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    else:
      wf1 = 7
      wf2 = 33333
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444


  elif(avg_amb>=25 and avg_amb<35):
    t1 =  25
    t2 =  35

    if(wf<4):
      wf1 = -33333
      wf2 = 4
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    elif(wf>=4 and wf<7):
      wf1 = 4
      wf2 = 7
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    else:
      wf1 = 7
      wf2 = 33333
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

        
  else:

    t1 =  35
    t2 =  22222

    if(wf<4):
      wf1 = -33333
      wf2 = 4
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    elif(wf>=4 and wf<7):
      wf1 = 4
      wf2 = 7
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444

    else:
      wf1 = 7
      wf2 = 33333
      if(sg<0.80):
        s1 =  -44444
        s2 =  0.80
      elif(sg>=0.80 and sg<0.90):
        s1 =  0.80
        s2 =  0.90
      elif(sg>=0.90 and sg<1.0):
        s1 =  0.90
        s2 =  1.0
      else:
        s1 =  1.0
        s2 =  44444


  return t1,t2, wf1,wf2,s1, s2
# print all_data 


#-------------------Regression------------------##

def multivariate_reg(x1, x2, y):
  x1 = np.array(x1)
  x2 = np.array(x2)
  y = np.array(y)
  A = array([x1,x2])
  w = linalg.lstsq(A.T,y)[0] # obtaining the parameters
  #print
  line = w[0]*x1+w[1]*x2 # regression line
  print 'multivariate fitting parameters is  for category'
  #print w
  return w

def lin_reg(x1, y, s, cl):
  x = np.array(x1)
  y=  np.array(y)
  #xi = arange(0,9)
  #print 'inside lin reg'
  #print x
  #print y
  minX  =  x[0]
  maxX =  x[0]
  minY = y[0]
  maxY  = y[0]

  for i in range (1, len(x)):
    if(minX > x[i]):
      minX = x[i]
    if(maxX<x[i]):
      maxX  = x[i] 
    if(minY > y[i]):
      minY =  y[i]
    if(maxY < y[i]):
      maxY =  y[i]

  #A = array([x])
  # linearly generated sequence
  #y = [19, 20, 20.5, 21.5, 22, 23, 23, 25.5, 24]
  def fitFunc(x, a):
    return a*x
  # w = linalg.lstsq(A.T,y)[0] # obtaining the parameters
  # # plotting the line
  # print 'lin reg parameter for category '
  # print w[0]
  # plt.ylabel('lin reg category',  fontsize = 16)
  # plt.xlabel('lin reg category', fontsize = 16)
  # line = w[0]*x # regression line
  # plot(x,line,'r-',x,y,'o')
  # show()
  #noisy = y + 0.25*np.random.normal(size=len(y))
  fitParams, fitCovariance= curve_fit(fitFunc, x, y)
  #print 'lin reg fit parameter is for category '
  print fitParams
  #print 'lin reg covariance is for category '
  print fitCovariance
  #rcParams['figure.figsize'] = 10, 6 
  plt.ylabel('lin reg category', fontsize = 16)
  plt.xlabel('lin reg category', fontsize = 16)
  #plt.xlim(minX,maxX)
  # plot the data as yelow circles with vertical errorbars
  #plt.ylim(minY, maxY)

  plt.errorbar(x, y, fmt = 'yo', yerr = 0.2)
  sigma = [fitCovariance[0,0], \
         ]
  # now plot the best fit curve and also +- 1 sigma curves
  # (the square root of the diagonal covariance matrix  
  # element is the uncertianty on the fit parameter.)
  plt.plot(x, fitFunc(x, fitParams[0]),\
     x, fitFunc(x, fitParams[0] + sigma[0]),\
     x, fitFunc(x, fitParams[0] - sigma[0])\
    )
  #plt.show()
  #plt.savefig('lin_reg'+s+str(cl)+'.png',  bbox_inches=0, dpi=400)
  return fitParams

def poly_reg(x1,y1, s, cl):
  x  = []
  y = []
  for i in range(0, len(x1)):
    if(x1[i]>0):
      x.append(x1[i])
      y.append(y1[i])

  x = np.array(x)
  y=  np.array(y)
  
  minX  =  x[0]
  maxX =  x[0]
  minY = y[0]
  maxY  = y[0]

  for i in range (1, len(x)):
    if(minX > x[i]):
      minX = x[i]
    if(maxX<x[i]):
      maxX  = x[i] 
    if(minY > y[i]):
      minY =  y[i]
    if(maxY < y[i]):
      maxY =  y[i]

  def fitFunc(x, a, b):
    #print x
    return a*np.power(x, b)

 #ooooo temp = fitFunc(x, 1.3, 0.5)
  #print 'tempLengh is' , len(temp)

  #noisy = y + 0.25*np.random.normal(size=len(y))

  fitParams, fitCovariance= curve_fit(fitFunc, x, y)
  #print 'poly reg fit parameter is for category '
  #print fitParams
  #print 'poly reg covariance is for category '
  #print fitCovariance
  #rcParams['figure.figsize'] = 10, 6 
  plt.ylabel('poly reg category', fontsize = 16)
  plt.xlabel('poly reg category', fontsize = 16)
  #plt.xlim(minX,maxX)
  # plot the data as red circles with vertical errorbars
  #plt.ylim(minY, maxY)

  plt.errorbar(x, y, fmt = 'yo', yerr = 0.2)
  sigma = [fitCovariance[0,0], \
         fitCovariance[1,1], \
         ]

  # now plot the best fit curve and also +- 1 sigma curves
  # (the square root of the diagonal covariance matrix  
  # element is the uncertianty on the fit parameter.)
  plt.plot(x, fitFunc(x, fitParams[0], fitParams[1]),\
     x, fitFunc(x, fitParams[0] + sigma[0], fitParams[1] - sigma[1]),\
     x, fitFunc(x, fitParams[0] - sigma[0], fitParams[1] + sigma[1])\
    )
  #plt.show()
 # plt.savefig('poly_reg'+s+str(cl)+'.png',  bbox_inches=0, dpi=400)
  return fitParams


  #---------------------------ploting graph between heat temp drop and heat rditaion flow ---- #
def exp_reg(x2,y):
  x = np.array(x2)
  y=  np.array(y)
  minX  =  x[0]
  maxX =  x[0]
  minY = y[0]
  maxY  = y[0]

  for i in range (1, len(x)):
    if(minX > x[i]):
      minX = x[i]
    if(maxX<x[i]):
      maxX  = x[i] 
    if(minY > y[i]):
      minY =  y[i]
    if(maxY < y[i]):
      maxY =  y[i]

  def fitFunc(x, a, b, c):
    #import bigfloat
# bigfloat.exp(5000,bigfloat.precision(100))
    return a*np.exp(-b*x)+c

  fitParams, fitCovariances= curve_fit(fitFunc, x, y)
  #print 'exp reg fit parameter for category '
  #print fitParams
  #print 'exp reg covariance for category'
  #print fitCovariances
  #rcParams['figure.figsize'] = 10, 6 
  plt.ylabel('exp reg category ', fontsize = 16)
  plt.xlabel('exp reg category ', fontsize = 16)
  #plt.xlim(minX,maxX)
  # plot the data as red circles with vertical errorbars
  #plt.ylim(minY, maxY)

  plt.errorbar(x, y, fmt = 'ro', yerr = 0.0)
  # now plot the best fit curve and also +- 1 sigma curves
  # (the square root of the diagonal covariance matrix  
  # element is the uncertianty on the fit parameter.)

  plt.plot(x, fitFunc(x, fitParams[0], fitParams[1], fitParams[2]),\
    )
  #plt.savefig('exp_reg.png')
  #show()
  return fitParams

def mean_normalization(x):
  s = 0
  for i in range(0,len(x)):
    s+=x[i]

  avg =  s/len(x)
  minX  =  x[0]
  maxX =  x[0]

  for i in range (1, len(x)):
    if(minX > x[i]):
      minX = x[i]
    if(maxX<x[i]):
      maxX  = x[i] 
  rnge =  maxX-minX

  for i in range(0, len(x)):
    x[i] =  (x[i]-avg)/rnge
  return x

def mean_normalization_pow_reg(x,y):
  s = 0
  x1 = []
  y1 = []
  count = 0
  for i in range(0,len(x)):
    if(x[i]>0):
      s+=x[i]
      count+=1
      y1.append(y[i])
      x1.append(x[i])

  x=  x1
  y = y1

  avg =  s/len(x)
  minX  =  x[0]
  maxX =  x[0]

  for i in range (1, len(x)):
   
    if(minX > x[i]):
      minX = x[i]
    if(maxX<x[i]):
      maxX  = x[i] 

  rnge =  maxX-minX
  for i in range(0, len(x)):
    x[i] =  (x[i]-avg)/rnge
  return x, y1

# x1_n = mean_normalization(x1)

# x2_n =  mean_normalization(x2)
# y_n =  mean_normalization(y)


# print 'graph with nomalizations'
# print len(x1_n), len(x2_n), len(y_n)
# w = multivariate_reg(x1_n, x2_n, y_n)

# print 'mupltivariate reg line due to feature heat cond and radiation', w
# print 'y vs x1 (t1-t2)'
# w = lin_reg(x1_n, y_n)
# print 'line reg for feature heat conduction', w
# x1_n_p , y_n_p=  mean_normalization_pow_reg(x1, y)
# w = poly_reg(x1_n_p, y_n_p)
# print 'poly reg for feature heat conduction', w
# w = exp_reg(x1_n, y_n)

# print 'exponential reg for feature heat conduction ', w
# print 'y vs x2 (t1^4-t2^4)'
# w = lin_reg(x2_n, y_n)
# print 'line reg for feature heat conduction', w
# x2_n_p , y_n_p=  mean_normalization_pow_reg(x2, y)
# w = poly_reg(x2_n_p, y_n_p)
# print 'poly reg for feature heat conduction', w
# w = exp_reg(x2_n, y)
# print 'exponential reg for feature heat conduction ', w

def find_constant(xx1, xx2, yy, cl):
  x11 = xx1
  x22 =  xx2
  y1=  yy

  const = {}
  if(len(x11)):
    try:
    #  print 'finding constant for this class ', d
      print '#------------------------------------------#'
      print 'graph without nomalizations'
      print len(x11), len(x22), len(y1)
      wm_1_2 = multivariate_reg(x11, x22, y1)
      print 'mupltivariate reg line due to feature heat cond and radiation', wm_1_2
      print
      print 'y vs x1 (t1-t2)'
      wl_1 = lin_reg(x11, y1, 'l1_',cl)
      print 'line reg for feature heat conduction', wl_1
      wp_1 = poly_reg(x11, y1, 'p1_',cl)
      print 'poly reg for feature heat conduction', wp_1
      #w = exp_reg(x1, y)
      #print 'exponential reg for feature heat conduction ', w
      print 'y vs x2 (t1^4-t2^4)'
      wl_2 = lin_reg(x22, y1, 'l2_',cl)
      print 'line reg for feature heat conduction', wl_2
      #x2_n_p , y_n_p=  mean_normalization_pow_reg(x2, y
      wp_2 = poly_reg(x22, y1, 'p2_',cl)
      print 'poly reg for feature heat conduction', wp_2
      #w = exp_reg(x2, y)
      #print 'exponential reg for feature heat conduction ', w
      const= {'wm_1_2_0':wm_1_2[0], 'wm_1_2_1':wm_1_2[1], 'wl_1': wl_1, 'wp_1_0':wp_1[0], 'wp_1_1':wp_1[1], 'wl_2':wl_2, 'wp_2_0':wp_2[0], 'wp_2_1':wp_2[1]}
    except:
      print 'inner try class have some poor data or no data so it cannot return covariabce or parameters' 
      pass
  else:
    #c= {'wm_1_2_0':0, 'wm_1_2_1':0, 'wl_1': 0, 'wp_1_0':0, 'wp_1_1':0, 'wl_2':0, 'wp_2_0':0, 'wp_2_1':0}
    const ={}

  
  return const


def get_futures_array(all_data):
  xx1 = []
  xx2 = []
  yy = []

 # print 'inside get futures '
  for key in all_data.keys():
    chpId =  key
    vess_data =  getVesselData(chpId)
    for m in range(0, len(all_data[key])-1):
      dhtdate =  all_data[key][m]['dht_date']
      dhtid =  all_data[key][m]['dht_id']
     # print dhtdate
      qry =  "select dht_id, dht_date,temp_type, air_temp, sw_temp from dht_head where chp_id ='"+str(chpId)+"' and bc_cargo_heating='0.0' and dht_id = '"+str(dhtid)+"'"
      cursor.execute(qry)
     # try:
        
      #print all_data[chpId]
      rows= cursor.fetchall()
      if(len(rows)>0 and rows[0]['air_temp']!=0 and rows[0]['sw_temp']!=0):
        air_temp = rows[0]['air_temp']
        sea_temp = rows[0]['sw_temp']
        temp_type = rows[0]['temp_type']

        #print
        #print 'current dht_id and data is', all_data[key][i]['dht_date'] , ' ',all_data[key][i]['dht_id']
        #print'chp id is', chpId,  'next dhtdate for non heating is',rows[0]['dht_date'] , ' ', rows[0]['dht_id']

        qry =  "select dht_id, dht_date,temp_type, air_temp, sw_temp from dht_head where chp_id ='"+str(chpId)+"' and bc_cargo_heating='0.0' and dht_date > '"+str(dhtdate)+"' order by dht_date"
        cursor.execute(qry)
        rows= cursor.fetchall()
        #print 'next dht_date', rows

        if(len(rows)>0):
          
          if(rows[0]['dht_date']==dhtdate+timedelta(1)):

            #print 'detail for tank ', all_data[key][i]['tank'] ,'and avg temp is', all_data[key][i]['avg_temp'] 
            #print 'chpid and current dht_date and dht_id is', chpId, ' ', all_data[key][m]['dht_date'], ' ', all_data[key][m]['dht_id']
            #print 'next dhtdate and dhtid  is',rows[0]['dht_date'] , ' ', rows[0]['dht_id']
            #print 'vess_data is', vess_data
            grade_data = getGradeData(chpId, all_data[key][m]['dht_id'])
            #print 'current day grade data is', grade_data
            tank_data = getTankData(vess_data, grade_data, all_data[key][m]['dht_id'], air_temp, sea_temp, temp_type)
            #print 'tank data is', tank_data
            grade_data_next = getGradeData(chpId,rows[0]['dht_id'])
            #print 'lenght of grade data is', len(grade_data), len(grade_data_next)
            #print 'next  day grade data is ', grade_data_next
            if(len(grade_data) == len(grade_data_next)):
                       
              qry =  "select temp_type from dht_head where dht_id = '"+str(rows[0]['dht_id'])+"'"
              cursor.execute(qry)
              row =  cursor.fetchone()
              temp_type_next =  row['temp_type']
              tanks_temp_next = getNextDayTanksTemp(vess_data, grade_data_next, rows[0]['dht_id'], temp_type_next)
              
              #print 'tank  next temp', tanks_temp_next
              #print tanks_temp_next[0][1]['name'], 'temp',  tanks_temp_next[0][1]['avg_temp']
              #print 'calculating heat flow for tank ,  chp_id, dht_id', all_data[key][m]['tank'], ' ', vess_data['chp_id'], ' ', all_data[key][m]['dht_id']
              x1, x2, y=  calcHeatFlowTank(tank_data, grade_data, vess_data, tanks_temp_next, all_data[key][m]['tank'], air_temp, sea_temp)
              print 'x1 ia', x1 , 'x2 ia', x2, 'y ia', y
              if((x1!=-1 and x2!=-1 and y!=0)):
                xx1.append(x1)
                xx2.append(x2)
                yy.append(y)

      # print 'future till now is'
      # print len(xx1)
      # print xx1
      # print len(xx2)
      # print xx2
      # print len(yy)
      # print yy        

  return xx1, xx2, yy

                       
DWT= [-11111, 34005.00,  36264.00 , 43716.00 , 63599.00 , 95649.00,146356.00, 11111111111111]
Tavg_Tamb = [-22222,15,25,35,22222]
WF = [-33333,4,7,33333]
SG = [-44444, 0.8, 0.9, 1.0, 44444]

all_level_class =[]
all_nodes_x1 =[]
all_nodes_x2 =[]
all_nodes_y = []
all_nodes_class = []
all_nodes_const = []

def get_all_node_classs_data():

  cl = 0
  for i in range(0, len(DWT)-1):
    for j in range(0, len(Tavg_Tamb)-1):
      for k in range(0, len(WF)-1):
        for l in range(0, len(SG)-1):

          d= {'dwt1':DWT[i], 'dwt2': DWT[i+1], 't1':Tavg_Tamb[j], 't2':Tavg_Tamb[j+1], 'wf1': WF[k], 'wf2':WF[k+1], 'sg1':SG[l], 'sg2':SG[l+1]}
          print 'class is ', d
          all_data = get_data_class(DWT[i],DWT[i+1],Tavg_Tamb[j],Tavg_Tamb[j+1], WF[k], WF[k+1], SG[l], SG[l+1])
         # print 'all_dat for this category is', all_data
          xx1,xx2,yy = get_futures_array(all_data)

          x11 =  xx1
          x22= xx2
          y1 =  yy
          const = find_constant(x11, x22, y1, cl)

          cl+=1  
          all_nodes_class.append(d)
          all_nodes_const.append(const)

          all_nodes_x1.append(xx1)
          all_nodes_x2.append(xx2)
          all_nodes_y.append(yy)


          print '#-----finidng data and constant for leaves nodes----##'
        
          print 'current class node  is ', d
          print 'constant is', const
          print 'all array future length for this classs is', ' ', len(xx1),' ', len(xx2),' ', len(yy)
          
         
        print '#----finding data for level 3 internal nodes ----####'
        d= {'dwt1':DWT[i], 'dwt2': DWT[i+1], 't1':Tavg_Tamb[j], 't2':Tavg_Tamb[j+1], 'wf1': WF[k], 'wf2':WF[k+1], 'sg1':SG[0], 'sg2':SG[len(SG)-1]}
        all_data = get_data_class(DWT[i],DWT[i+1],Tavg_Tamb[j],Tavg_Tamb[j+1], WF[k], WF[k+1], SG[0], SG[len(SG)-1])
        xx1,xx2,yy = get_futures_array(all_data)
        
        x11 =  xx1
        x22= xx2 
        y1 =  yy
        const = find_constant(x11, x22, y1, cl)
        all_nodes_class.append(d)
        all_nodes_const.append(const)

        all_nodes_x1.append(xx1)
        all_nodes_x2.append(xx2)
        all_nodes_y.append(yy)

        print 'current class node  is ', d
        print 'constant is', const
        print 'all array future length for this classs is', ' ', len(xx1),' ', len(xx2),' ', len(yy)

      print '#-----finding data for level 2 nodes----####'
      d= {'dwt1':DWT[i], 'dwt2': DWT[i+1], 't1':Tavg_Tamb[j], 't2':Tavg_Tamb[j+1], 'wf1': WF[0], 'wf2':WF[len(WF)-1], 'sg1':SG[0], 'sg2':SG[len(SG)-1]}
      all_data = get_data_class(DWT[i],DWT[i+1],Tavg_Tamb[j],Tavg_Tamb[j+1], WF[0], WF[len(WF)-1], SG[0], SG[len(SG)-1])
      xx1,xx2,yy = get_futures_array(all_data)
      
      x11 =  xx1
      x22= xx2
      y1 =  yy
      const = find_constant(x11, x22, y1, cl)

      all_nodes_class.append(d)
      all_nodes_const.append(const)

      all_nodes_x1.append(xx1)
      all_nodes_x2.append(xx2)
      all_nodes_y.append(yy)

      print 'current class node  is ', d
      print 'constant is', const
      print 'all array future length for this classs is', ' ', len(xx1),' ', len(xx2),' ', len(yy)

    print '#-----finding constant and data for level-1 nodes -----###'
    d= {'dwt1':DWT[i], 'dwt2': DWT[i+1], 't1':Tavg_Tamb[0], 't2':Tavg_Tamb[len(Tavg_Tamb)-1], 'wf1': WF[0], 'wf2':WF[len(WF)-1], 'sg1':SG[0], 'sg2':SG[len(SG)-1]}
    all_data = get_data_class(DWT[i],DWT[i+1],Tavg_Tamb[0],Tavg_Tamb[len(Tavg_Tamb)-1], WF[0], WF[len(WF)-1], SG[0], SG[len(SG)-1])
    xx1,xx2,yy = get_futures_array(all_data)
    
    x11 =  xx1
    x22= xx2
    y1 =  yy
    const = find_constant(x11, x22, y1, cl)
    
    all_nodes_class.append(d)
    all_nodes_const.append(const)

    all_nodes_x1.append(xx1)
    all_nodes_x2.append(xx2)
    all_nodes_y.append(yy)

    print 'current class node  is ', d
    print 'constant is', const
    print 'all array future length for this classs is', ' ', len(xx1),' ', len(xx2),' ', len(yy)

  print '#-----finding constant and data for root node -----###'
  d= {'dwt1':DWT[0], 'dwt2': DWT[len(DWT)-1], 't1':Tavg_Tamb[0], 't2':Tavg_Tamb[len(Tavg_Tamb)-1], 'wf1': WF[0], 'wf2':WF[len(WF)-1], 'sg1':SG[0], 'sg2':SG[len(SG)-1]}
  all_data = get_data_class(DWT[0],DWT[len(DWT)-1],Tavg_Tamb[0],Tavg_Tamb[len(Tavg_Tamb)-1], WF[0], WF[len(WF)-1], SG[0], SG[len(SG)-1])
  xx1,xx2,yy = get_futures_array(all_data)
  
  x11 =  xx1
  x22= xx2
  y1 =  yy
  const = find_constant(x11, x22, y1, cl)
  all_nodes_class.append(d)
  all_nodes_const.append(const)

  all_nodes_x1.append(xx1)
  all_nodes_x2.append(xx2)
  all_nodes_y.append(yy)

  print 'current class node  is ', d
  print 'constant is', const
  print 'all array future length for this classs is', ' ', len(xx1),' ', len(xx2),' ', len(yy)

  return all_nodes_class, all_nodes_const, all_nodes_x1, all_nodes_x2, all_nodes_y

#------------------------------testing on a chpid -----------------__##

def get_class_and_data_chpid(chp_id):

  x_1 = []
  x_2 = []
  y_1_2 = []

  chpId=  chp_id
  qry1= "select min(dht_date) from dht_head where chp_id = '"+str(chpId)+"'"
  cursor.execute(qry1)
  row =  cursor.fetchone()

  qry ="select  dh.dht_date,dh.voy_no,dh.temp_type, dh.sw_temp, dh.wind_force, dh.air_temp, ct.grade_no, ct.ext_load_temp ,ct.api_sp_gravity, ct.temp_dispatch_port from dht_head dh,chp_trans ct where dh.chp_id = '"+str(chpId)+"' and "+\
  "dh.dht_date >='"+str(row['min(dht_date)'])+"' and dh.sw_temp<>0 and dh.air_temp<> 0 and  dh.chp_id=ct.chp_id and bc_cargo_heating = 0 order by dht_date "

  cursor.execute(qry)
  row =  cursor.fetchall()[0]


  if(row['sw_temp'] and row['air_temp']):

    #print 'rows for avg_amb', row
    amb_temp =  (float(row['sw_temp'])+float(row['air_temp']))/2
    row['amb_temp'] =  amb_temp
    #print 'row amb is', row['amb_temp']
    vn =  row['voy_no']
    wf =  row['wind_force']
    avg_temp = (float(row['ext_load_temp'])+float(row['temp_dispatch_port']))/2
    #print 'avg temp is', avg_temp
    avg_amb =  avg_temp - amb_temp
    if(row['temp_type'] =='F'):
      row['ext_load_temp'] =  (row['ext_load_temp']-32)*5/9
      row['temp_dispatch_port'] =  (row['temp_dispatch_port']-32)*5/9

    if(row['api_sp_gravity']>1.2):
      row['api_sp_gravity'] = (141.5/(131.5 + float(row['api_sp_gravity'])))

    if(row['api_sp_gravity']<0.7):
      row['api_sp_gravity'] = (141.5/(131.5 + float(row['api_sp_gravity'])))

    sg =  row['api_sp_gravity']

    print 'wind_force ', wf
    print 'print sg is', sg
    qry  ="select distinct(vess_id) from dht_head where chp_id = '"+str(chpId)+"'"
    cursor.execute(qry)
    row =  cursor.fetchone()
    print 'vess_idd is', row['vess_id']
    qry =  "select DWT from dimensionmaster where vess_id ='"+str(row['vess_id'])+"'"
    cursor.execute(qry)
    row =  cursor.fetchone()
    print 'DWT is', row['DWT']
    dwt =  row['DWT']

    print 'iitial classifier for chpId', chpId
    print  dwt, avg_amb, wf, sg

    dwt1=dwt2=t1=t2=wf1=wf2=sg1=sg2 = 0
    DWT= [-11111, 34005.00,36264.00,43716.00, 63599.00 , 95649.00,146356.00, 11111111111111]

    #for tank_data in tank_grade_api['tanks']:
    dwt1=dwt2=t1=t2=wf1=wf2=sg1=sg2 = 0
    # tanks_data['tanks'][i]['avg_amb'] = float(tanks_data['tanks'][i]['avg_temp'])-float(tanks_data['amb_temp'])
    # avg_amb = tank_grade_api['tanks'][i]['avg_amb']
    # sg = tank_grade_api['tanks'][i]['api_sp_gravity']
    #print 'dwt is', dwt
    if dwt >= DWT[6]:
      dwt1 = DWT[6]
      dwt2 = 11111111111111
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)
    
    if(dwt>=DWT[5] and dwt< DWT[6]):
      dwt1 =DWT[5]
      dwt2 = DWT[6]
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)
    
    if(dwt >=DWT[4]and dwt<DWT[5]):
      dwt1 = DWT[4]
      dwt2 = DWT[5]
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)
    
    if(dwt >=DWT[3]  and dwt<DWT[4]):
      dwt1 =  DWT[3]
      dwt2 = DWT[4]
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)

    if(dwt >=DWT[2] and dwt<DWT[3]):
      dwt1 = DWT[2]
      dwt2 = DWT[3]
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)  

    if(dwt >=DWT[1] and dwt<DWT[2]):
      dwt1 = DWT[1]
      dwt2 = DWT[2]
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)
    
    if(dwt<DWT[1]):
      dwt1 = -11111
      dwt2 = DWT[1]
      t1,t2,wf1,wf2,sg1,sg2 = get_path_to_class(avg_amb, wf, sg)


    print 'final classified data is'
    print dwt1, dwt2, t1, t2, wf1, wf2, sg1, sg2

    all_data = get_data_class(dwt1,dwt2, t1, t2, wf1, wf2, sg1, sg2)
    print 'classess are ', all_data
    

    # print 'all data'

    # print all_data.keys()
    # for key in all_data.keys():
    #   chpId =  key
    #   print 'all dht_id for chp_id is'
    #   print all_data[chpId]
    for key in all_data.keys():
    #for k  in range(0,1):
      #chpId= 260

      chpId =  key
      print 'analysis for chpId', chpId
      print 'all dht for chpid ', chpId
      print all_data[chpId]
      #all_data[key]= OrderedDict(sorted(all_data[key].items(), key=lambda kv: kv[1]['dht_date']))
      #key =  chpId
      vess_data =  getVesselData(chpId)
      for m in range(0, len(all_data[key])-1):
        dhtdate =  all_data[key][m]['dht_date']
        dhtid =  all_data[key][m]['dht_id']
       # print dhtdate
        qry =  "select dht_id, dht_date,temp_type, air_temp, sw_temp from dht_head where chp_id ='"+str(chpId)+"' and bc_cargo_heating='0.0' and dht_id = '"+str(dhtid)+"'"
        cursor.execute(qry)
        try:
          #print all_data[chpId]
          rows= cursor.fetchall()
          if(len(rows)>0 and rows[0]['air_temp']!=0 and rows[0]['sw_temp']!=0):
            air_temp = rows[0]['air_temp']
            sea_temp = rows[0]['sw_temp']
            temp_type = rows[0]['temp_type']

            #print
            #print 'current dht_id and data is', all_data[key][i]['dht_date'] , ' ',all_data[key][i]['dht_id']
            #print'chp id is', chpId,  'next dhtdate for non heating is',rows[0]['dht_date'] , ' ', rows[0]['dht_id']

            qry =  "select dht_id, dht_date,temp_type, air_temp, sw_temp from dht_head where chp_id ='"+str(chpId)+"' and bc_cargo_heating='0.0' and dht_date > '"+str(dhtdate)+"' order by dht_date"
            cursor.execute(qry)
            rows= cursor.fetchall()
            #print 'next dht_date', rows

            if(len(rows)>0):
              
              if(rows[0]['dht_date']==dhtdate+timedelta(1)):
                #print 'detail for tank ', all_data[key][i]['tank'] ,'and avg temp is', all_data[key][i]['avg_temp'] 
                print 'chpid and current dht_date and dht_id is', chpId, ' ', all_data[key][m]['dht_date'], ' ', all_data[key][m]['dht_id']
                #print 'next dhtdate and dhtid  is',rows[0]['dht_date'] , ' ', rows[0]['dht_id']
                #print 'vess_data is', vess_data
                grade_data = getGradeData(chpId, all_data[key][m]['dht_id'])
                #print 'current day grade data is', grade_data
                tank_data = getTankData(vess_data, grade_data, all_data[key][m]['dht_id'], air_temp, sea_temp, temp_type)
                #print 'tank data is', tank_data
                grade_data_next = getGradeData(chpId,rows[0]['dht_id'])
                #print 'lenght of grade data is', len(grade_data), len(grade_data_next)
                #print 'next  day grade data is ', grade_data_next

                if(len(grade_data) == len(grade_data_next)):
                  
                  qry =  "select temp_type from dht_head where dht_id = '"+str(rows[0]['dht_id'])+"'"
                  cursor.execute(qry)
                  row =  cursor.fetchone()
                  temp_type_next =  row['temp_type']
                  tanks_temp_next = getNextDayTanksTemp(vess_data, grade_data_next, rows[0]['dht_id'], temp_type_next)
                  
                  #print 'tank  next temp', tanks_temp_next
                  #print tanks_temp_next[0][1]['name'], 'temp',  tanks_temp_next[0][1]['avg_temp']
                  print 'calculating heat flow for tank ,  chp_id, dht_id', all_data[key][m]['tank'], ' ', vess_data['chp_id'], ' ', all_data[key][m]['dht_id']
                  x1, x2, y=  calcHeatFlowTank(tank_data, grade_data, vess_data, tanks_temp_next, all_data[key][m]['tank'], air_temp, sea_temp)
                  print 'x1', x1 , 'x2', x2, 'y', y
                  if((x1!=-1 and x2!=-1 and y!=0)):
                    x_1.append(x1)
                    x_2.append(x2)
                    y_1_2.append(y)
                  #print 'data till chpid', chpId
                  #print 'xx1 is', len(xx1) , ' ', xx1
                  #print 'xx2 is', len(xx2) , ' ', xx2
                  #print 'y is', len(yy) , ' ', yy

        except:
          print 'chpid and dht for index out of range', chpId, all_data[key][m]['dht_id'], 'and date is', all_data[key][m]['dht_date']

    print
    print
    print 'VECTORS x1 , x2 and y is for this category'
    print
    print len(x_1), x_1
    print
    print len(x_2), x_2
    print
    print len(y_1_2) , y_1_2

  return x_1, x_2, y_1_2

##############FUNCTION CALLING FOR DIFFERENT PURPOSE###########################################
def get_chpid_costant(x1,x2,y, chpid):
  x11 =  x1
  x22= x2
  y1 =  y
  const = {}
  try:
    if(len(x11)):
      try:
        print 'finding constant for this class chpid  ', chpid
        print '#------------------------------------------#'
        print 'graph without nomalizations'
        print len(x11), len(x22), len(y1)
        wm_1_2 = multivariate_reg(x11, x22, y1)
        print 'mupltivariate reg line due to feature heat cond and radiation', wm_1_2
        print
        print 'y vs x1 (t1-t2)'
        wl_1 = lin_reg(x11, y1, 'l1_',chpid)
        print 'line reg for feature heat conduction', wl_1
        wp_1 = poly_reg(x11, y1, 'p1_',chpid)
        print 'poly reg for feature heat conduction', wp_1
        #w = exp_reg(x1, y)
        #print 'exponential reg for feature heat conduction ', w
        print 'y vs x2 (t1^4-t2^4)'
        wl_2 = lin_reg(x22, y1, 'l2_',chpid)
        print 'line reg for feature heat conduction', wl_2
        #x2_n_p , y_n_p=  mean_normalization_pow_reg(x2, y
        wp_2 = poly_reg(x22, y1, 'p2_',chpid)
        print 'poly reg for feature heat conduction', wp_2
        #w = exp_reg(x2, y)
        #print 'exponential reg for feature heat conduction ', w
        const= {'wm_1_2_0':wm_1_2[0], 'wm_1_2_1':wm_1_2[1], 'wl_1': wl_1, 'wp_1_0':wp_1[0], 'wp_1_1':wp_1[1], 'wl_2':wl_2, 'wp_2_0':wp_2[0], 'wp_2_1':wp_2[1]}
      except:
        print 'inner try class category chpid ' , chpid ,'have some poor data or no data so it cannot return covariabce or parameters' 
        pass

    else:

      #c= {'wm_1_2_0':0, 'wm_1_2_1':0, 'wl_1': 0, 'wp_1_0':0, 'wp_1_1':0, 'wl_2':0, 'wp_2_0':0, 'wp_2_1':0}
      const ={}
      print 'there is no data for the category chpid belong ', chpid

  except:
     print 'outer try class chpid cattegory ' , chpid ,'have some poor data or no data so it cannot return covariabce or parameters' 
     pass
  return const




# print 'data for chpid 1579'
# x1,x2,y = get_class_and_data_chpid(1579)
# const =  get_chpid_costant(x1,x2,y, 1579)
# print 'constant for 1579' , const

# print

# print 'data for chpid 1516'
# x1,x2,y = get_class_and_data_chpid(1516)
# const =  get_chpid_costant(x1,x2,y, 1516)
# print 'constant for 1516' , const
# #1579, 1612, 1482, 1604
# print

# print 'data for chpid 1612'
# x1,x2,y  =  get_class_and_data_chpid(1612)
# print
# const =  get_chpid_costant(x1,x2,y, 1612)
# print 'constant for 1612' , const


# print 'data for chpid 1482'
# x1,x2,y  = get_class_and_data_chpid(1482)
# print
# const =  get_chpid_costant(x1,x2,y, 1482)
# print 'constant for 1482' , const

# print 'data for chpid 1604'
# x1,x2,y =get_class_and_data_chpid(1604)
# print
# const =  get_chpid_costant(x1,x2,y, 1604)
# print 'constant for 1604' , const


all_class_nodes, all_class_nodes_const, final_x1, final_x2,final_y = get_all_node_classs_data()

# DWT= [-11111, 34005.00,  36264.00 , 43716.00 , 63599.00 , 95649.00,146356.00, 11111111111111]
# Tavg_Tamb = [-22222,15,25,35,22222]
# WF = [-33333,4,7,33333]
# SG = [-44444, 0.8, 0.9, 1.0, 44444]




print "_____________________final array nodes and constant______________"

print 'lenght of all 5 euqal array is (equal to toal nodes in tree )is '
print len(all_class_nodes), ' ', len(all_class_nodes_const),' ',len(final_x1) , ' ', len(final_x2), ' ', len(final_y) 
print 'final array of array of all class of future x1', len(final_x1)
print final_x1

print 'final array of array of all class of future\ x2', len(final_x2)
print final_x2

print 'final array of array of all class of y values', len(final_y)
print final_y

print '__________________________________-nodes and constant are ---------------'
print len(all_level_class)
print all_class_nodes
print
print
print len(all_class_nodes_const)
print all_class_nodes_const

cursor.close ()
conn.close ()