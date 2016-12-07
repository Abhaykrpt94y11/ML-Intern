import numpy as np
from numpy import *
import getdata as vd
import MySQLdb
import json
from datetime import timedelta
import CalcHeatFlow as ch
import math

conn = MySQLdb.connect (host = "localhost",user = "root", passwd = "", db = "heatsolc")
cursor = conn.cursor (MySQLdb.cursors.DictCursor)

def getFirstChp(chpId):
	chp = {}
	qry = "select vess_id from chp_head where chp_id = '"+str(chpId)+"'"
	cursor.execute(qry)
	vid = cursor.fetchone()

	qry ="select DWT from dimensionmaster where vess_id = '"+str(vid['vess_id'])+"'"
	cursor.execute(qry)
	dwt = cursor.fetchone()

	chp['DWT'] = float(dwt['DWT'])
	qry ="select total_grade from chp_head where chp_id = '"+str(chpId)+"'"
	cursor.execute(qry)
	row = cursor.fetchone()
	total_grade =  row['total_grade']
	print 'total_grade is from chp_head', total_grade
	if(chpId==1516):
		total_grade =1
	qry =  "select dht_id, dht_date from dht_head where chp_id ='"+str(chpId)+"' order by dht_date"
	cursor.execute (qry)
	rows= cursor.fetchall()

	for row in rows:
		qry="select count(distinct(dt.cargo_grade)),ct.api_sp_gravity from dht_trans dt, chp_trans ct where ct.chp_id='"+str(chpId)+"' and "+\
		"ct.chp_id = dt.chp_id and dt.dht_id = '"+str(row['dht_id'])+"' and ct.grade_no =  dt.cargo_grade"
		cursor.execute (qry)
		ro= cursor.fetchone()

		if(total_grade == ro['count(distinct(dt.cargo_grade))']):
			chp['dht_id'] = row['dht_id']
			chp['first_dht_date'] = row['dht_date']
			chp['total_grade'] =  ro['count(distinct(dt.cargo_grade))']
	
			chp['tanks']=[]
			print 'total actual grade by counting grade_no from dht_trans', ro['count(distinct(dt.cargo_grade))']
			qry = "select dt.avg_temp, dt.tank, dt.cargo_grade, ct.api_sp_gravity from dht_trans dt, chp_trans ct "+\
			"where dt.chp_id = '"+str(chpId)+"' and dt.dht_id = '"+str(chp['dht_id'])+"' and dt.qty<>0 "+\
			"and ct.chp_id = dt.chp_id and ct.grade_no = dt.cargo_grade  "
			cursor.execute (qry)
			all_tank_detail= cursor.fetchall()

			qry="select sw_temp, air_temp, wind_force from dht_head where chp_id = '"+str(chpId)+"' and dht_id = '"+str(chp['dht_id'])+"'"
			cursor.execute (qry)
			sw_air_wf= cursor.fetchone()
			amb_temp =(float(sw_air_wf['sw_temp'])+float(sw_air_wf['air_temp']))/2
			chp['amb_temp'] = amb_temp
			chp['wind_force'] =float(sw_air_wf['wind_force'])
			chp['air_temp'] =  float(sw_air_wf['air_temp'])
			chp['sea_temp']  =  float(sw_air_wf['sw_temp'])

			for tank in all_tank_detail:
				if(tank['api_sp_gravity']>1.2 or tank['api_sp_gravity']<0.7):
					tank['api_sp_gravity'] = (141.5/(131.5 + float(tank['api_sp_gravity'])))

				tank['sh'] =  ((float(tank['avg_temp']) + 32) * 1.8 + 671) * (2.1- float(tank['api_sp_gravity']))/2030 * 1/0.2388
				avg_amb =  float(tank['avg_temp'])-amb_temp
				tank['avg_amb'] =avg_amb
				chp['tanks'].append(tank)

			break

	return chp

# w0 = -0.393694507887
# w= [ -5.44907187e+04 ,  4.55892315e-06,   4.45739879e+04]

# #for last last 625 chpid fuel cons data
# #b = [7.00790276002e-06, 0.000168031289602, 0.0134008689111 ]

# #b = [ 2.72773494,  0.80089694]
# #b = [ 8.03419147, 0.69642961]
# #b=  [3.60469012 , 0.77516466]

# b =[-3.60480324,  0.77516167]


def TempPolyFitFunc(x, b, m, sh, t1):
   heat_loss =  b[0]*np.power(x, b[1])
   t2 =  t1+(heat_loss/(m*sh))
   return t2

def TempLineFitFunc(x, w0, m, sh, t1):
	heat_loss =  x*w0
	t2 =  t1+(heat_loss/(m*sh))
	return t2

def TempExpnFitFunc(x, w, m, sh, t1 ):
	heat_loss = w[0]*np.exp(w[1]*x)+w[2]
	t2 =  t1+(heat_loss/(m*sh))
	return t2

def calcNextDayGradeTemp(tank, grade, vess):

   	try:
	    for k in range(1, vess['total_grade']+1):
	      	avgTemp =0 
	      #	print 'for k'
	      	qty =  0
	      	for i in range(0, 2):
	        	for j in range(0, vess['tank_system']):
	        #		print 'inside j '
	        		try:
		          		if(tank[i][j]['cargo_id']==k):
		          			avgTemp +=float(tank[i][j]['avg_temp'])*float(tank[i][j]['quantity'])
		          			qty+=float(tank[i][j]['quantity'])
		          	except:
		          		pass
	      	#print 'inside calcGradeTemp', k-1 
	      	if(qty>0):
	        	avgTemp =avgTemp/float(qty)
	        	grade[k-1].update({'temp':avgTemp})
	    	#  print 'avg temp of grade ', k, ' is', grade[k-1]['temp']
	     	# print 'grade k is ', grade[k-1
  	except:
  		pass
  	return grade
  

def calcNextDayFuelCons(ngrade, vess, pgrade, b):
	a1 = 0.0
	a2 = 0.0
	a3 = 0.0
	try:
		for i in range(0, vess['total_grade']):

			t1 = float(grade[i]['sum(dt.qty)'])* float(grade[i]['api_sp_gravity'])*(float(ngrade[i]['temp'])-float(pgrade[i]['temp']))
			a1+=t1
			t2 = math.pow(float(grade[i]['sum(dt.qty)']), 2.0/3) *((float(ngrade[i]['temp'])+float(pgrade[i]['temp']))/2-20)
			a2+=t2
			t3 = 100-20
			a3+=t3		
	except:
		pass
	return b[0]*a1+b[1]*a2+b[2]*a3


def NextDayTankTemp(vess, tanks, tanks_data):
	tank =  tanks
	#print 'before funcall'
	#print tanks
	t2_lin = 0
	for k in range(0, len(tanks_data['tanks'])):
		for i in range(0,2):
			for j in range(0, vess['tank_system']):
				if(tanks_data['tanks'][k]['tank'] == tanks[i][j]['name']):
					heat_flow= tanks[i][j]['heatloss']
					w0 = tanks_data['tanks'][k]['const']['wl_1']
					b0= tanks_data['tanks'][k]['const']['wp_1_0']
					b1 =tanks_data['tanks'][k]['const']['wp_1_1']
					b=[b0, b1]

					print tanks[i][j]['sh'], 'api sh', tanks_data['tanks'][k]['sh']

				#	print 'heat flow is', heat_flow
					#t2 = voyage_details.tanks[i][j]['avg_temp'] - voyage_details.tanks[i][j]['heatloss']/(voyage_details.tanks[i][j]['quantity']*voyage_details.tanks[i][j]['sh'])
					t2_lin = TempLineFitFunc(heat_flow, w0, tanks[i][j]['quantity'], tanks[i][j]['sh'],tanks[i][j]['avg_temp'])
					#t2_exp =  TempExpnFitFunc(heat_flow, w, tanks[i][j]['quantity'], tanks[i][j]['sh'], tanks[i][j]['avg_temp'])
					t2_poly = TempPolyFitFunc(heat_flow, b, tanks[i][j]['quantity'], tanks[i][j]['sh'], tanks[i][j]['avg_temp'])
					print 'predicted temp oftank ',tanks[i][j]['name'], 'tank', tanks_data['tanks'][k]['tank'], 'is ', 'qty',tanks[i][j]['quantity'], 'temp LineFit is', t2_lin , 'poly fit is', t2_poly

					tank[i][j]['avg_temp'] = t2_lin
					tanks_data['tanks'][k]['avg_temp'] =  t2_lin

		#tanks_data['tanks'][k]['avg_temp'] = tank[i][j]		
	return tank, tanks_data

	# for i in range(0, 2):
	# 		for j in range(0,vess['tank_system']):
	# 			#try:
	# 				#if()
	# 			#	d = {}
	# 				#print 'before heatloss'
	# 				#print 'next day temp of tank i, j ',tanks[i][j]['name'],  i ,' ', j , ' is', 'qty is ',tanks[i][j]['quantity'], 'and dht_id is',vess['dht_id']
	# 				#print 'before heatloss'

	# 			heat_flow= tanks[i][j]['heatloss']
	# 			w0 = tanks_data['const']['wl_1']
	# 			b0= tanks_data['const']['wp_1_0']
	# 			b1 =tanks_data['const']['wp_1_1']
	# 			b=[b0, b1]
	# 			print tanks[i][j]['sh'], 'api sh', tanks_data['sh']
	# 		#	print 'heat flow is', heat_flow
	# 			#t2 = voyage_details.tanks[i][j]['avg_temp'] - voyage_details.tanks[i][j]['heatloss']/(voyage_details.tanks[i][j]['quantity']*voyage_details.tanks[i][j]['sh'])
	# 			t2_lin = TempLineFitFunc(heat_flow, w0, tanks[i][j]['quantity'], tanks[i][j]['sh'],tanks[i][j]['avg_temp'])
	# 			#t2_exp =  TempExpnFitFunc(heat_flow, w, tanks[i][j]['quantity'], tanks[i][j]['sh'], tanks[i][j]['avg_temp'])
	# 			t2_poly = TempPolyFitFunc(heat_flow, b, tanks[i][j]['quantity'], tanks[i][j]['sh'], tanks[i][j]['avg_temp'])
	# 			print 'predicted temp oftank ',tanks[i][j]['name'], 'tank', tanks_data['tanks'][], 'is ', 'qty',tanks[i][j]['quantity'], 'temp LineFit is', t2_lin , 'poly fit is', t2_poly

	# 			tank[i][j]['avg_temp'] = t2_lin
	# 			tanks_data['tanks']['avg_temp'] =  t2_lin

				#tank[i].append(d)			
				#except:
					#pass
	#print tank
	#print 'afterfuncall'
	#print tanks
	#return tank


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



def get_sw_air_temp(chp_id, dht_id):

	chpId = chp_id
	qry ="select  dh.dht_date, dh.voy_no,dh.temp_type, dh.sw_temp, dh.wind_force, dh.air_temp, ct.grade_no, ct.ext_load_temp , ct.temp_dispatch_port from dht_head dh,chp_trans ct where dh.chp_id = '"+str(chpId)+"' and "+\
  	"dh.dht_dht_id ='"+str(dht_id)+"' and dh.sw_temp<>0 and dh.air_temp<> 0 and  dh.chp_id=ct.chp_id"
  	cursor.execute(qry)
  	row =  cursor.fetchall()
  	return float(row[sw_temp]), float(row['air_temp'])



def getCargoHeatingTotalFuel(chpId, dhtId):

	qry ="select dht_date, cargo_heating_total_fo from dht_head where dht_id = '"+str(dhtId)+"' and chp_id= '"+str(chpId)+"'"
	cursor.execute(qry)
	row = cursor.fetchone()
	#vess_dat['date'] =  row['dht_date']
	#print 'cfo date is', row['dht_date']
	return row['cargo_heating_total_fo']



def make_plan_per_day(tanks_data,  chpId, dhtId):

	voyage_details=vd.VoyageDetails(chpId, dhtId)
	##-----getting weather data on that date ----- ##
	fo_cons =  getCargoHeatingTotalFuel(chpId, dhtId)
	voyage_details.grades = ch.updateGradeTemp(voyage_details.tanks, voyage_details.grades)

	if(chpId == 1516):
		for k in range(1, 1+1):
			print 'grade ', k  , 'load temp',  voyage_details.grades[k-1]['ext_load_temp']
			print 'grade ', k, 'transit temp', voyage_details.grades[k-1]['temp_during_transit']
			print 'grade', k, 'discharge temp',  voyage_details.grades[k-1]['temp_dispatch_port']
			print

	# print 'voyage detials are'
	# print voyage_details.tanks

	tanks = ch.CalcHeatFlow(voyage_details.tanks, voyage_details.grades, voyage_details.vessel, tanks_data['air_temp'], tanks_data['sea_temp'])		
 
	grades =   ch.updateGradeTemp(voyage_details.tanks, voyage_details.grades)
	#print grades
	print 
	print
	# date =  tanks_data['first_dht_date']
	# #for d in range(0, no_of_days):
	print 'current date fuel oil consumption is'
	print fo_cons
	# print 'plan for date is', current_date
	if(fo_cons>0.0):
		tank =  NextDayTankTemp(voyage_details.vessel, tanks , tanks_data)
		print 'next day tank details is'
		print tank
		grades =   ch.updateGradeTemp(tanks, grades)
		print 'previous day grade temp'
		print grades
		grade = calcNextDayGradeTemp(tank, voyage_details.grades, voyage_details.vessel)
		print 'next day grade detail'
		print grade

		for k in range(1, voyage_details.vessel['total_grade']+1):
			#print 'grade ', k, 'transit temp', voyage_details.grades[k-1]['temp_during_transit']
			if(grade[k-1]['temp'] > voyage_details.grades[k-1]['temp_during_transit'] ):
				k = 1
		#tanks = ch.CalcHeatFlow(tank, grade, voyage_details.vessel, air_temp, sea_temp)

	else:

		tank, tanks_data =  NextDayTankTemp(voyage_details.vessel, tanks , tanks_data)
		#print 'next day tank details is'
		#print tank
		grades =   ch.updateGradeTemp(tanks, voyage_details.grades)
		#print 'previous day grade temp'
		#print grades
		grade = calcNextDayGradeTemp(tank, voyage_details.grades, voyage_details.vessel)
		#print 'next day grade detail'
		#print grade

		if(chpId == 1516):
			for k in range(1, 1+1):
				#print 'grade ', k, 'transit temp', voyage_details.grades[k-1]['temp_during_transit']
				if(grade[k-1]['temp'] > voyage_details.grades[k-1]['temp_during_transit'] ):
					k = 1
		#tanks = ch.CalcHeatFlow(tank, grade, voyage_details.vessel, air_temp, sea_temp)
		#print
		#tank =  tanks
		#date +=timedelta(1)


	return tanks_data

def getIndexLevelConst(cls):
	print 'inside'
	print cls
	for j  in range(0, len(all_temp_class)):
		if(all_temp_class[j] ==cls):
			print 'constant for class ', cls
			print all_temp_const[j]
			# print 'length of total data x1 ', len(all_x1[j])
			# print all_x1[j]
			
			# print 'length of total data y ', len(all_y[j])
			# print all_y[j]
			# print 'class is' , cls
			# print 'constant for this class',  all_temp_const[j]
			#print j
	return j

def getDailyConstantTank(tank_grade_api):
	#print 'tank grade detai on this day is', tank_grade_api
	dhtId =  tank_grade_api['dht_id']

	#print 'chp start date is', tank_grade_api['first_dht_date']
	print
	dwt = tank_grade_api['DWT']
	#print 'dwt is', dwt
	wf = tank_grade_api['wind_force']
	#DWT= [-11111, 34005.00,36264.00,43716.00, 63599.00 , 95649.00,146356.00, 11111111111111]	


	DWT= [-11111, 34005.00,36264.00,43716.00, 63599.00 , 95649.00,146356.00, 11111111111111]



	for i in range(0 , len(tank_grade_api['tanks'])):
	#for tank_data in tank_grade_api['tanks']:
		dwt1=dwt2=t1=t2=wf1=wf2=sg1=sg2 = 0
		tanks_data['tanks'][i]['avg_amb'] = float(tanks_data['tanks'][i]['avg_temp'])-float(tanks_data['amb_temp'])
		avg_amb = tank_grade_api['tanks'][i]['avg_amb']
		sg = tank_grade_api['tanks'][i]['api_sp_gravity']
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
	  	print 'final classified data is for tank', tank_grade_api['tanks'][i]['tank']
	  	print dwt1, dwt2, t1, t2, wf1, wf2, sg1, sg2
	  	cls = {'sg1': sg1, 'sg2': sg2, 'wf2': wf2, 'dwt2': dwt2, 'dwt1': dwt1, 'wf1': wf1, 't2': t2, 't1': t1}
	  	print 'detail for tank name', tank_grade_api['tanks'][i]['tank']


		j = getIndexLevelConst(cls)
		print 'legnth of jthe', len(all_y[j])
		if(len(all_y[j])>150):
			tank_grade_api['tanks'][i]['const'] = all_temp_const[j]
		if(len(all_y[j])<150):
			while len(all_y[j])<150:
				print 'in while lopp'
				if(sg1 ==1.0):
					sg1 =0.9
					sg2 =1.0
					cls = {'sg1': sg1, 'sg2': sg2, 'wf2': wf2, 'dwt2': dwt2, 'dwt1': dwt1, 'wf1': wf1, 't2': t2, 't1': t1}
					j = getIndexLevelConst(cls)
					if(len(all_y[j]) >150):
						# print 'length of total data x1 ', len(all_x1[j])
						# print all_x1[j]
						
						print 'length of total data y ', len(all_y[j])
						print all_y[j]
						print 'class is' , cls
						print 'constant for this class',  all_temp_const[j]
						tank_grade_api['tanks'][i]['const'] = all_temp_const[j]
						break


				if(sg1 ==0.9):
					sg1 =0.8
					sg2 =0.9

					cls = {'sg1': sg1, 'sg2': sg2, 'wf2': wf2, 'dwt2': dwt2, 'dwt1': dwt1, 'wf1': wf1, 't2': t2, 't1': t1}
					j = getIndexLevelConst(cls)
					if(len(all_y[j]) >150):
						# print 'length of total data x1 ', len(all_x1[j])
						# print all_x1[j]

						print 'length of total data y ', len(all_y[j])
						print all_y[j]
						print 'class is' , cls
						print 'constant for this class',  all_temp_const[j]
						tank_grade_api['tanks'][i]['const'] = all_temp_const[j]
						break

	return tank_grade_api

def getDailyPlan():

	current_date =  tank_grade_api['first_dht_date']
	next_date = current_date+timedelta(1)
	temp_tank = make_plan_per_day(tank_data, chpId, dhtId)

	tank_grade_api['etd_discharge_port'] = voyage_details.grades[tank_data['cargo_grade']-1]['etd_discharge_port']
	voyage =  tank_grade_api['etd_discharge_port'] - tank_grade_api['first_dht_date']
	no_of_days =  voyage.days
	print 'etd etd_discharge_port', tank_grade_api['etd_discharge_port']
	print 'no of days is', no_of_days
	dhtId=  tank_grade_api['dht_id']
	qry = "select dht_id from dht_head where chp_id ='"+str(chpId)+"' and dht_date = '"+str(next_date)+"'"
	cursor.execute(qry)

	next_dhtId = cursor.fetchone()['dht_id']
	current_date = next_date


#-----------------Making plan started --- Whoooooooooooaaaa------- !!!!!

all_temp_const = [{}, {'wm_1_2_0': -0.36724937952356523, 'wm_1_2_1': 2.5407652514318023e-07, 'wl_1': array([-0.31257212]), 'wl_2': array([ -1.26050735e-06]), 'wp_2_1': 0.50050554157904781, 'wp_1_0': -0.55924785221893725, 'wp_1_1': 0.92918582193996402, 'wp_2_0': -0.039266510754693187}, {}, {'wm_1_2_0': -0.57042906032279417, 'wm_1_2_1': 4.1579290022666659e-06, 'wl_1': array([-0.16076747]), 'wl_2': array([ -1.31465969e-06]), 'wp_2_1': 0.49270443114764362, 'wp_1_0': -2.1272493956149088, 'wp_1_1': 0.71590576498078073, 'wp_2_0': -0.049024161708229007}, {'wm_1_2_0': -0.16277976162527436, 'wm_1_2_1': -3.2299558394858789e-07, 'wl_1': array([-0.20577648]), 'wl_2': array([ -1.27774560e-06]), 'wp_2_1': 0.47163404339190174, 'wp_1_0': -4.4634549946673596, 'wp_1_1': 0.6451911055703563, 'wp_2_0': -0.072500569211519095}, {}, {'wm_1_2_0': -0.33930528329324749, 'wm_1_2_1': 2.5852988176818823e-07, 'wl_1': array([-0.29502712]), 'wl_2': array([ -1.44840550e-06]), 'wp_2_1': 0.24812936288346443, 'wp_1_0': -35.484698881269239, 'wp_1_1': 0.4037994937855186, 'wp_2_0': -6.3476802386432505}, {}, {'wm_1_2_0': -1.0034216332685617, 'wm_1_2_1': 6.881280911324414e-06, 'wl_1': array([-0.32224426]), 'wl_2': array([ -2.24959414e-06]), 'wp_2_1': 0.97919255395694949, 'wp_1_0': -1.7030166898371699, 'wp_1_1': 0.82773655711343808, 'wp_2_0': -6.3794099263929886e-06}, {'wm_1_2_0': -0.49021093460337473, 'wm_1_2_1': 1.3914769009072053e-06, 'wl_1': array([-0.31103036]), 'wl_2': array([ -1.69932574e-06]), 'wp_2_1': 0.39637710971516343, 'wp_1_0': -0.19719989955371658, 'wp_1_1': 1.0718287836875953, 'wp_2_0': -0.44704309348359489}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.31411939320743593, 'wm_1_2_1': 4.3275448076959858e-07, 'wl_1': array([-0.25748776]), 'wl_2': array([ -1.47532394e-06]), 'wp_2_1': 0.39457450442354713, 'wp_1_0': -3.359300476855791, 'wp_1_1': 0.70557160206990621, 'wp_2_0': -0.4050087574281005}, {}, {'wm_1_2_0': -0.11047688592819352, 'wm_1_2_1': -1.0062302486028088e-06, 'wl_1': array([-0.41004314]), 'wl_2': array([ -1.35736666e-06]), 'wp_2_1': 0.86649417709938359, 'wp_1_0': -0.1760079805786311, 'wp_1_1': 1.0988253503264198, 'wp_2_0': -2.3237622071100033e-05}, {}, {'wm_1_2_0': -0.44354367331058414, 'wm_1_2_1': 1.5031894148379324e-06, 'wl_1': array([-0.269598]), 'wl_2': array([ -2.26264768e-06]), 'wp_2_1': 0.39078442582561923, 'wp_1_0': -12.445117260074712, 'wp_1_1': 0.57011166965826121, 'wp_2_0': -0.65248571473331818}, {'wm_1_2_0': -0.14933791326421075, 'wm_1_2_1': -8.852598984924544e-07, 'wl_1': array([-0.39069717]), 'wl_2': array([ -1.37793204e-06]), 'wp_2_1': 0.81997081786571901, 'wp_1_0': -0.83637190812551221, 'wp_1_1': 0.91146595367755712, 'wp_2_0': -6.3231337486792152e-05}, {}, {'wm_1_2_0': -0.80298303831352402, 'wm_1_2_1': 2.4216233370584284e-06, 'wl_1': array([-0.24550965]), 'wl_2': array([ -9.76726016e-07]), 'wp_2_1': -0.13545562986441478, 'wp_1_0': -628.37261082526368, 'wp_1_1': 0.09330594616954857, 'wp_2_0': -23501.480785119224}, {}, {'wm_1_2_0': 0.62114125825222632, 'wm_1_2_1': -7.7547338212239388e-06, 'wl_1': array([-0.32504667]), 'wl_2': array([ -2.79596013e-06]), 'wp_2_1': 1.4751363819709455, 'wp_1_0': -8.1032712672989202, 'wp_1_1': 0.63945313072303545, 'wp_2_0': -1.4709251399249501e-10}, {'wm_1_2_0': -0.43363431633898059, 'wm_1_2_1': 8.3328806277883761e-07, 'wl_1': array([-0.27325207]), 'wl_2': array([ -1.21470215e-06]), 'wp_2_1': -0.0030575239049260585, 'wp_1_0': -7.8434722454755414, 'wp_1_1': 0.61617349626425177, 'wp_2_0': -1719.7720090221442}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.18539554789215432, 'wm_1_2_1': -6.2437653262223379e-07, 'wl_1': array([-0.32939219]), 'wl_2': array([ -1.32580181e-06]), 'wp_2_1': 0.61058263751624409, 'wp_1_0': -5.0890133153565413, 'wp_1_1': 0.68434616950603511, 'wp_2_0': -0.0050042432253464683}, {}, {'wm_1_2_0': 0.13486584164403737, 'wm_1_2_1': -1.1521716581817335e-06, 'wl_1': array([-0.45423613]), 'wl_2': array([ -9.11613337e-07]), 'wp_2_1': 1.1945207182740312, 'wp_1_0': 5.4412485020431749, 'wp_1_1': -1.7202413948718351, 'wp_2_0': -1.108173581108129e-08}, {}, {}, {'wm_1_2_0': 0.13486584164403731, 'wm_1_2_1': -1.1521716581817333e-06, 'wl_1': array([-0.45423613]), 'wl_2': array([ -9.11613337e-07]), 'wp_2_1': 1.1945207206044619, 'wp_1_0': 6.7126553721871094, 'wp_1_1': -1.7718445125370721, 'wp_2_0': -1.1081735224389159e-08}, {}, {'wm_1_2_0': -0.35061172848199401, 'wm_1_2_1': 4.3184441635165347e-07, 'wl_1': array([-0.25614034]), 'wl_2': array([ -1.04176192e-06]), 'wp_2_1': 0.30159918086312859, 'wp_1_0': -3.7234418210937883, 'wp_1_1': 0.70016502146326687, 'wp_2_0': -3.0632730448517798}, {}, {}, {'wm_1_2_0': -0.35061172848199401, 'wm_1_2_1': 4.3184441635165347e-07, 'wl_1': array([-0.25614034]), 'wl_2': array([ -1.04176192e-06]), 'wp_2_1': 0.30159918086312859, 'wp_1_0': -3.7234418210937883, 'wp_1_1': 0.70016502146326687, 'wp_2_0': -3.0632730448517798}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.10537199536984808, 'wm_1_2_1': -6.8579493234821789e-07, 'wl_1': array([-0.31440938]), 'wl_2': array([ -9.51112032e-07]), 'wp_2_1': 0.86221619716034148, 'wp_1_0': -5.2066083846173066e-07, 'wp_1_1': 2.4585318222120831, 'wp_2_0': -2.0314540017747708e-05}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.18645530920047446, 'wm_1_2_1': -5.3617047960940252e-07, 'wl_1': array([-0.30904935]), 'wl_2': array([ -1.16093928e-06]), 'wp_2_1': 0.6459055673475006, 'wp_1_0': -0.39103287693561301, 'wp_1_1': 0.97562246581466106, 'wp_2_0': -0.0023875509355116677}, {}, {}, {'wm_1_2_0': -0.5908667702180066, 'wm_1_2_1': 7.2841775150144488e-07, 'wl_1': array([-0.53732809]), 'wl_2': array([ -4.34241539e-06]), 'wp_2_1': 0.22617534399545514, 'wp_1_0': -0.53733886625760152, 'wp_1_1': 0.99999776023626574, 'wp_2_0': -37.910421875042601}, {}, {'wm_1_2_0': -0.5908667702180066, 'wm_1_2_1': 7.2841775150144488e-07, 'wl_1': array([-0.53732809]), 'wl_2': array([ -4.34241539e-06]), 'wp_2_1': 0.22617534399545514, 'wp_1_0': -0.53733886625760152, 'wp_1_1': 0.99999776023626574, 'wp_2_0': -37.910421875042601}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.60019789246090871, 'wm_1_2_1': 1.0219465603889762e-06, 'wl_1': array([-0.51944145]), 'wl_2': array([ -3.94741110e-06]), 'wp_2_1': 0.17717869900836783, 'wp_1_0': -0.47387529025232861, 'wp_1_1': 1.0102630869742035, 'wp_2_0': -95.551881805289568}, {}, {}, {'wm_1_2_0': -0.4260174924748123, 'wm_1_2_1': -1.8376426902371276e-08, 'wl_1': array([-0.42937959]), 'wl_2': array([ -2.14683186e-06]), 'wp_2_1': 0.54589433513975061, 'wp_1_0': -0.2405292192900346, 'wp_1_1': 1.0620673303388029, 'wp_2_0': -0.038741367470091929}, {}, {'wm_1_2_0': -0.4260174924748123, 'wm_1_2_1': -1.8376426902371276e-08, 'wl_1': array([-0.42937959]), 'wl_2': array([ -2.14683186e-06]), 'wp_2_1': 0.54589433513975061, 'wp_1_0': -0.2405292192900346, 'wp_1_1': 1.0620673303388029, 'wp_2_0': -0.038741367470091929}, {}, {}, {'wm_1_2_0': -0.6369597853126201, 'wm_1_2_1': 1.5072900893607027e-06, 'wl_1': array([-0.30973451]), 'wl_2': array([ -1.29702879e-06]), 'wp_2_1': 0.17506468340524334, 'wp_1_0': -2.6510542354454891, 'wp_1_1': 0.77380486984758179, 'wp_2_0': -84.902481438852206}, {}, {'wm_1_2_0': -0.6369597853126201, 'wm_1_2_1': 1.5072900893607027e-06, 'wl_1': array([-0.30973451]), 'wl_2': array([ -1.29702879e-06]), 'wp_2_1': 0.17506468340524334, 'wp_1_0': -2.6510542354454891, 'wp_1_1': 0.77380486984758179, 'wp_2_0': -84.902481438852206}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.50119822904251088, 'wm_1_2_1': 4.0990493378278379e-07, 'wl_1': array([-0.41939152]), 'wl_2': array([ -1.93424265e-06]), 'wp_2_1': 0.53913091718162054, 'wp_1_0': -0.17457954129022882, 'wp_1_1': 1.0931321473885383, 'wp_2_0': -0.042887003555533126}, {}, {}, {'wm_1_2_0': -0.57105821617081831, 'wm_1_2_1': 5.6524110830216052e-07, 'wl_1': array([-0.40593257]), 'wl_2': array([ -9.35940895e-07]), 'wp_2_1': -0.038074413275552138, 'wp_1_0': -0.2540119195280201, 'wp_1_1': 1.0477977160443728, 'wp_2_0': -15424.294433760775}, {}, {'wm_1_2_0': -0.57105821617081831, 'wm_1_2_1': 5.6524110830216052e-07, 'wl_1': array([-0.40593257]), 'wl_2': array([ -9.35940895e-07]), 'wp_2_1': -0.038074413275552138, 'wp_1_0': -0.2540119195280201, 'wp_1_1': 1.0477977160443728, 'wp_2_0': -15424.294433760775}, {}, {}, {'wm_1_2_0': -0.46412135244707053, 'wm_1_2_1': -1.4725796850404429e-07, 'wl_1': array([-0.48947343]), 'wl_2': array([ -2.69428632e-06]), 'wp_2_1': 0.46793540066187378, 'wp_1_0': -6.725103368325696, 'wp_1_1': 0.73166685860240066, 'wp_2_0': -0.30738622882065197}, {}, {'wm_1_2_0': -0.46412135244707065, 'wm_1_2_1': -1.472579685040468e-07, 'wl_1': array([-0.48947343]), 'wl_2': array([ -2.69428632e-06]), 'wp_2_1': 0.46793535261465208, 'wp_1_0': -6.7251015704058181, 'wp_1_1': 0.73166688606277397, 'wp_2_0': -0.30738655039252755}, {}, {}, {'wm_1_2_0': -0.76498836809477, 'wm_1_2_1': 1.8041644009465606e-06, 'wl_1': array([-0.51393996]), 'wl_2': array([ -3.24896616e-06]), 'wp_2_1': 0.14812329317836095, 'wp_1_0': -0.25990100951793083, 'wp_1_1': 1.0695045959661882, 'wp_2_0': -352.09817974210097}, {}, {'wm_1_2_0': -0.76498836809477, 'wm_1_2_1': 1.8041644009465606e-06, 'wl_1': array([-0.51393996]), 'wl_2': array([ -3.24896616e-06]), 'wp_2_1': 0.14812329317836095, 'wp_1_0': -0.25990100951793083, 'wp_1_1': 1.0695045959661882, 'wp_2_0': -352.09817974210097}, {'wm_1_2_0': -0.58769055986641161, 'wm_1_2_1': 5.9773118471288098e-07, 'wl_1': array([-0.45707095]), 'wl_2': array([ -1.39072870e-06]), 'wp_2_1': 0.055090068178033656, 'wp_1_0': -1.3140157038294331, 'wp_1_1': 0.89213681247009979, 'wp_2_0': -2210.4130698255244}, {}, {}, {'wm_1_2_0': -0.4972110867097202, 'wm_1_2_1': -5.4407553690711428e-08, 'wl_1': array([-0.50827361]), 'wl_2': array([ -2.40147303e-06]), 'wp_2_1': 0.61966313085555136, 'wp_1_0': -1.0570060658838247, 'wp_1_1': 0.9273914229215503, 'wp_2_0': -0.011898568169850727}, {}, {'wm_1_2_0': -0.4972110867097202, 'wm_1_2_1': -5.4407553690711428e-08, 'wl_1': array([-0.50827361]), 'wl_2': array([ -2.40147303e-06]), 'wp_2_1': 0.61966313085555136, 'wp_1_0': -1.0570060658838247, 'wp_1_1': 0.9273914229215503, 'wp_2_0': -0.011898568169850727}, {}, {'wm_1_2_0': -0.88446395504589281, 'wm_1_2_1': 9.4225064316427819e-07, 'wl_1': array([-0.74441895]), 'wl_2': array([ -4.83913765e-06]), 'wp_2_1': 0.56112144749040904, 'wp_1_0': -1.4936491223693658, 'wp_1_1': 0.93079729283218826, 'wp_2_0': -0.077313727095208853}, {'wm_1_2_0': -0.55646556669996117, 'wm_1_2_1': 1.2082947413809017e-07, 'wl_1': array([-0.52513274]), 'wl_2': array([ -1.84938992e-06]), 'wp_2_1': 0.29750290741931962, 'wp_1_0': -103.77338253479329, 'wp_1_1': 0.47380286004612071, 'wp_2_0': -14.795791247988305}, {}, {'wm_1_2_0': -0.65167582468738272, 'wm_1_2_1': 4.2554216843226364e-07, 'wl_1': array([-0.54575648]), 'wl_2': array([ -1.94273871e-06]), 'wp_2_1': 0.24943761947529425, 'wp_1_0': -69.129041127392185, 'wp_1_1': 0.51815638228091054, 'wp_2_0': -45.184352964459208}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.57956316410517161, 'wm_1_2_1': 2.2805005018033189e-07, 'wl_1': array([-0.52671893]), 'wl_2': array([ -2.05466128e-06]), 'wp_2_1': 0.3738451107070061, 'wp_1_0': -13.403052577547005, 'wp_1_1': 0.67822192352071065, 'wp_2_0': -2.7617766610422381}, {'wm_1_2_0': -0.58001619421583395, 'wm_1_2_1': 4.4735168876927207e-07, 'wl_1': array([-0.48197657]), 'wl_2': array([ -1.75160595e-06]), 'wp_2_1': 0.38467186068373066, 'wp_1_0': -0.36354413259096052, 'wp_1_1': 1.0286478153548706, 'wp_2_0': -1.6672461932541782}, {}, {'wm_1_2_0': -0.50079377406886438, 'wm_1_2_1': 8.9781683070384358e-07, 'wl_1': array([-0.29945104]), 'wl_2': array([ -1.32208730e-06]), 'wp_2_1': 1.1584959787181877, 'wp_1_0': -0.010076430345291052, 'wp_1_1': 1.3756738007030733, 'wp_2_0': -4.4777459923590632e-08}, {'wm_1_2_0': 0.10413298407887624, 'wm_1_2_1': -2.7762676671047603e-06, 'wl_1': array([-0.27558369]), 'wl_2': array([ -2.03276253e-06]), 'wp_2_1': 0.69133343628242516, 'wp_1_0': -1.1975706026964812, 'wp_1_1': 0.83921937962282489, 'wp_2_0': -0.0011933492532437053}, {'wm_1_2_0': -1.8536061443512057, 'wm_1_2_1': 7.7544135556039268e-06, 'wl_1': array([-0.57039353]), 'wl_2': array([ -3.31864989e-06]), 'wp_2_1': 0.064012453668292432, 'wp_1_0': -0.22537297674428397, 'wp_1_1': 1.114601470738626, 'wp_2_0': -506.27288920977577}, {'wm_1_2_0': -0.22118672712654311, 'wm_1_2_1': -3.3110937218762092e-07, 'wl_1': array([-0.28994212]), 'wl_2': array([ -1.36730500e-06]), 'wp_2_1': 0.74748336191253983, 'wp_1_0': -0.096750827429338326, 'wp_1_1': 1.1237964757371228, 'wp_2_0': -0.00029450684230643916}, {}, {}, {'wm_1_2_0': -0.2593141602756176, 'wm_1_2_1': -2.3325483104083887e-06, 'wl_1': array([-0.69147]), 'wl_2': array([ -3.62627913e-06]), 'wp_2_1': 0.57248401110103331, 'wp_1_0': -0.09316669289351133, 'wp_1_1': 1.2334706753749043, 'wp_2_0': -0.030022175263991788}, {}, {}, {}, {}, {}, {}, {}, {}, {'wm_1_2_0': -1.5422902200035578, 'wm_1_2_1': 4.010314552743616e-06, 'wl_1': array([-0.72245856]), 'wl_2': array([ -3.04992817e-06]), 'wp_2_1': -0.44719554175125792, 'wp_1_0': -1299750517.1778812, 'wp_1_1': -1.3163201182029338, 'wp_2_0': -100071064.81173864}, {'wm_1_2_0': -0.17948878633250659, 'wm_1_2_1': -6.2493652319693852e-07, 'wl_1': array([-0.34849545]), 'wl_2': array([ -1.27878000e-06]), 'wp_2_1': 1.1795316298723397, 'wp_1_0': 2.4571770157168902, 'wp_1_1': -1.7589507981723593, 'wp_2_0': -2.4852494333431974e-08}, {'wm_1_2_0': -0.5968314624192439, 'wm_1_2_1': 8.4630559462259274e-07, 'wl_1': array([-0.45062119]), 'wl_2': array([ -2.29516029e-06]), 'wp_2_1': 0.25224196750391431, 'wp_1_0': -0.13666545586184506, 'wp_1_1': 1.1283355382444962, 'wp_2_0': -22.029913911512217}, {}, {'wm_1_2_0': -0.6229437175674245, 'wm_1_2_1': 9.6032661187709818e-07, 'wl_1': array([-0.42198862]), 'wl_2': array([ -1.74921902e-06]), 'wp_2_1': 0.16533012860653667, 'wp_1_0': -0.10054641341099417, 'wp_1_1': 1.153991628695701, 'wp_2_0': -126.41928908659108}, {}, {'wm_1_2_0': 0.30823759043929805, 'wm_1_2_1': -2.6440328879479866e-06, 'wl_1': array([-0.37844612]), 'wl_2': array([ -1.48630423e-06]), 'wp_2_1': 1.3655459068404059, 'wp_1_0': 7.1061099936430487, 'wp_1_1': -2.0250193115367394, 'wp_2_0': -4.8151573080322092e-10}, {'wm_1_2_0': -0.1205163551175403, 'wm_1_2_1': -1.4457265264186469e-06, 'wl_1': array([-0.45140527]), 'wl_2': array([ -1.95728645e-06]), 'wp_2_1': 1.0793094760615123, 'wp_1_0': 2.2537657686547741, 'wp_1_1': -1.9190034598525032, 'wp_2_0': -3.4712961863944328e-07}, {}, {'wm_1_2_0': -0.68708610512521784, 'wm_1_2_1': 9.7271765563803922e-07, 'wl_1': array([-0.46033609]), 'wl_2': array([ -1.85619370e-06]), 'wp_2_1': 0.82182103193041323, 'wp_1_0': 5.9243033444637216, 'wp_1_1': -1.7673263181201175, 'wp_2_0': -9.0488269284005242e-05}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.60625622078975672, 'wm_1_2_1': 7.5500899940342729e-07, 'wl_1': array([-0.44087037]), 'wl_2': array([ -1.85288214e-06]), 'wp_2_1': 0.36895633940404704, 'wp_1_0': -0.0090895638187498354, 'wp_1_1': 1.4143591585815469, 'wp_2_0': -1.6700940060153888}, {}, {}, {}, {'wm_1_2_0': -0.16880690426681619, 'wm_1_2_1': -5.4062957815820034e-07, 'wl_1': array([-0.42792676]), 'wl_2': array([ -8.87851268e-07]), 'wp_2_1': 0.80870064015596843, 'wp_1_0': -0.036118865656868927, 'wp_1_1': 1.2532901562704617, 'wp_2_0': -7.0861505126987965e-05}, {}, {}, {}, {'wm_1_2_0': -0.45003142746764074, 'wm_1_2_1': -1.9245583568254365e-07, 'wl_1': array([-0.49590827]), 'wl_2': array([ -1.81484766e-06]), 'wp_2_1': 0.29264140169178915, 'wp_1_0': -0.87108301415187916, 'wp_1_1': 0.94202488396763406, 'wp_2_0': -12.942917568099752}, {'wm_1_2_0': 0.49486614201997114, 'wm_1_2_1': -1.8173682552145957e-06, 'wl_1': array([-0.33440079]), 'wl_2': array([ -7.45337990e-07]), 'wp_2_1': 1.0732444241840815, 'wp_1_0': -18.98728931878798, 'wp_1_1': 0.5855816743568435, 'wp_2_0': -1.4014708454870776e-07}, {'wm_1_2_0': -0.55798090892046426, 'wm_1_2_1': 3.1745430438882351e-07, 'wl_1': array([-0.46702787]), 'wl_2': array([ -1.30451902e-06]), 'wp_2_1': 0.063279502824956535, 'wp_1_0': -2.7556372358065397, 'wp_1_1': 0.81742193615139269, 'wp_2_0': -1871.6045954227725}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.53750439804212591, 'wm_1_2_1': 3.125521429252888e-07, 'wl_1': array([-0.45733533]), 'wl_2': array([ -1.39688598e-06]), 'wp_2_1': -0.036681105108741924, 'wp_1_0': -21.767961700423424, 'wp_1_1': 0.60250753758427555, 'wp_2_0': -16731.941896098233}, {}, {}, {'wm_1_2_0': -0.22033220503932571, 'wm_1_2_1': -7.6261357533960581e-07, 'wl_1': array([-0.4602086]), 'wl_2': array([ -1.34978219e-06]), 'wp_2_1': 0.57986005005587549, 'wp_1_0': -6.5265938974746405e-06, 'wp_1_1': 2.1106744701652773, 'wp_2_0': -0.020922125474769109}, {'wm_1_2_0': -0.60105293139413318, 'wm_1_2_1': -6.6488766041925325e-07, 'wl_1': array([-0.81071482]), 'wl_2': array([ -2.54680558e-06]), 'wp_2_1': 0.62870407709067699, 'wp_1_0': -3.8954149712822366, 'wp_1_1': 0.84218312204191936, 'wp_2_0': -0.011359226771183853}, {'wm_1_2_0': -0.24679689413879954, 'wm_1_2_1': -7.6199958389944178e-07, 'wl_1': array([-0.48652071]), 'wl_2': array([ -1.42967928e-06]), 'wp_2_1': 0.53720785265303983, 'wp_1_0': 3.2422977557544947, 'wp_1_1': -1.7065275980755974, 'wp_2_0': -0.058128991794232282}, {}, {}, {'wm_1_2_0': -0.31743284489525647, 'wm_1_2_1': -5.9565750117470464e-07, 'wl_1': array([-0.49842568]), 'wl_2': array([ -1.52007992e-06]), 'wp_2_1': 0.59565895262275503, 'wp_1_0': -6.7888622068862633e-05, 'wp_1_1': 1.8875706842424487, 'wp_2_0': -0.015497775508222228}, {'wm_1_2_0': 0.024072165587594396, 'wm_1_2_1': -1.2027833283241763e-06, 'wl_1': array([-0.51905602]), 'wl_2': array([ -1.15064645e-06]), 'wp_2_1': 1.219050319103272, 'wp_1_0': -0.072833835778337241, 'wp_1_1': 1.1948829217943904, 'wp_2_0': -7.2340253621553722e-09}, {'wm_1_2_0': -0.32312907202430546, 'wm_1_2_1': -5.0627239441778677e-07, 'wl_1': array([-0.50660322]), 'wl_2': array([ -1.31042327e-06]), 'wp_2_1': 0.57207911818197132, 'wp_1_0': 1.5011919420271427, 'wp_1_1': -1.7018551651932023, 'wp_2_0': -0.02452128701365295}, {}, {}, {'wm_1_2_0': -0.22276305906376109, 'wm_1_2_1': -5.3164948432811775e-07, 'wl_1': array([-0.39364972]), 'wl_2': array([ -1.17155015e-06]), 'wp_2_1': 0.50371962094336631, 'wp_1_0': -0.35313669502095746, 'wp_1_1': 1.0108533453372852, 'wp_2_0': -0.096992931302832652}, {}, {'wm_1_2_0': -0.22276305906376109, 'wm_1_2_1': -5.3164948432811775e-07, 'wl_1': array([-0.39364972]), 'wl_2': array([ -1.17155015e-06]), 'wp_2_1': 0.50371962094336631, 'wp_1_0': -0.35313669502095746, 'wp_1_1': 1.0108533453372852, 'wp_2_0': -0.096992931302832652}, {'wm_1_2_0': -0.27375612528354282, 'wm_1_2_1': -6.1770071160956394e-07, 'wl_1': array([-0.4852587]), 'wl_2': array([ -1.32605980e-06]), 'wp_2_1': 0.55964821703525425, 'wp_1_0': 1.0431527692822673, 'wp_1_1': -1.6938539852369212, 'wp_2_0': -0.032513915079684125}, {'wm_1_2_0': -0.41544015314422489, 'wm_1_2_1': -1.7886562930626076e-07, 'wl_1': array([-0.46686724]), 'wl_2': array([ -1.39596351e-06]), 'wp_2_1': 0.57385523215552325, 'wp_1_0': -0.02892498255551236, 'wp_1_1': 1.2839787448916062, 'wp_2_0': -0.021719490132906593}, {}, {}, {'wm_1_2_0': -1.397459494523112, 'wm_1_2_1': 4.4888792667172161e-06, 'wl_1': array([-0.57240527]), 'wl_2': array([ -2.34249742e-06]), 'wp_2_1': 0.35845622361558455, 'wp_1_0': -29.780450916947586, 'wp_1_1': 0.5586030073054743, 'wp_2_0': -2.2021691045805283}, {}, {'wm_1_2_0': -0.90625843746186852, 'wm_1_2_1': 9.7305987097674245e-07, 'wl_1': array([-0.70571068]), 'wl_2': array([ -3.23505080e-06]), 'wp_2_1': 1.3461193313565278, 'wp_1_0': -1.2966238793045903e-08, 'wp_1_1': 2.9553591584372541, 'wp_2_0': -2.0112997780926399e-09}, {}, {'wm_1_2_0': -0.43510847954395288, 'wm_1_2_1': -3.6756081723386542e-07, 'wl_1': array([-0.51425118]), 'wl_2': array([ -2.33849595e-06]), 'wp_2_1': 1.1173414602026519, 'wp_1_0': -0.0039246070898287929, 'wp_1_1': 1.5340566668966698, 'wp_2_0': -1.9038184394771505e-07}, {'wm_1_2_0': -0.63751879834031899, 'wm_1_2_1': 8.3242185980351309e-07, 'wl_1': array([-0.53400718]), 'wl_2': array([ -3.05277292e-06]), 'wp_2_1': 0.47866482970064955, 'wp_1_0': -0.58466535557303434, 'wp_1_1': 0.99045795582758034, 'wp_2_0': -0.18102509624040222}, {}, {'wm_1_2_0': -0.57803967678795398, 'wm_1_2_1': 3.0107502950084779e-07, 'wl_1': array([-0.52058249]), 'wl_2': array([ -2.44293830e-06]), 'wp_2_1': 0.5994990066517627, 'wp_1_0': -0.069080809493279452, 'wp_1_1': 1.2235488266948029, 'wp_2_0': -0.012902923124453635}, {}, {'wm_1_2_0': -0.87562483170232697, 'wm_1_2_1': 1.5273435560104119e-06, 'wl_1': array([-0.55997475]), 'wl_2': array([ -2.63244086e-06]), 'wp_2_1': 0.64453205778622058, 'wp_1_0': -1.4547347199289355, 'wp_1_1': 0.89486509278342752, 'wp_2_0': -0.0052433391804948912}, {'wm_1_2_0': 0.097584966281646368, 'wm_1_2_1': -6.2609954651673456e-06, 'wl_1': array([-0.68504226]), 'wl_2': array([ -5.48631801e-06]), 'wp_2_1': -0.061551045147779176, 'wp_1_0': -6436.6337938958577, 'wp_1_1': -0.096168929498906527, 'wp_2_0': -10004.402950631662}, {}, {'wm_1_2_0': -0.86874981686645836, 'wm_1_2_1': 1.4935207776566886e-06, 'wl_1': array([-0.56461725]), 'wl_2': array([ -2.67171529e-06]), 'wp_2_1': 0.53902438046846968, 'wp_1_0': -4.1138249088675654, 'wp_1_1': 0.7805406969830111, 'wp_2_0': -0.049944119432983311}, {'wm_1_2_0': -0.63530730874378849, 'wm_1_2_1': 2.6297121065924603e-07, 'wl_1': array([-0.58359621]), 'wl_2': array([ -2.73266823e-06]), 'wp_2_1': 0.755210074223441, 'wp_1_0': -0.011080887462484796, 'wp_1_1': 1.4381082713770881, 'wp_2_0': -0.00052071155701295148}, {}, {}, {'wm_1_2_0': -0.6440272100377441, 'wm_1_2_1': 2.6701637518464889e-07, 'wl_1': array([-0.54317002]), 'wl_2': array([ -1.36722333e-06]), 'wp_2_1': 0.2939470340291, 'wp_1_0': -95.407158629419158, 'wp_1_1': 0.47896665049262105, 'wp_2_0': -13.987883115975446}, {}, {'wm_1_2_0': -0.25792573217942755, 'wm_1_2_1': -1.0810727873759797e-06, 'wl_1': array([-0.55306625]), 'wl_2': array([ -1.93727386e-06]), 'wp_2_1': 0.92002015570224294, 'wp_1_0': -0.00020125833710441462, 'wp_1_1': 1.8201417625338572, 'wp_2_0': -1.1630381977472294e-05}, {}, {'wm_1_2_0': -0.085590653721908674, 'wm_1_2_1': -1.1292177809793294e-06, 'wl_1': array([-0.33938916]), 'wl_2': array([ -1.47514365e-06]), 'wp_2_1': 0.93233121444306932, 'wp_1_0': -0.0086539612877670081, 'wp_1_1': 1.3859067715015259, 'wp_2_0': -6.5395913822329437e-06}, {'wm_1_2_0': -0.27229234654123968, 'wm_1_2_1': -5.2784444921348675e-07, 'wl_1': array([-0.3615445]), 'wl_2': array([ -1.75913318e-06]), 'wp_2_1': 0.45493762774927321, 'wp_1_0': -1.6733660309977429, 'wp_1_1': 0.83384995348793745, 'wp_2_0': -0.25396135826728439}, {}, {'wm_1_2_0': -0.10663281309190728, 'wm_1_2_1': -1.1237089065900188e-06, 'wl_1': array([-0.35604109]), 'wl_2': array([ -1.55667775e-06]), 'wp_2_1': 0.85940953932682629, 'wp_1_0': -0.094357985354789939, 'wp_1_1': 1.1401039230136898, 'wp_2_0': -3.4276848156494746e-05}, {}, {'wm_1_2_0': -0.047550649509670855, 'wm_1_2_1': -9.5004742224896954e-07, 'wl_1': array([-0.22543472]), 'wl_2': array([ -1.20116572e-06]), 'wp_2_1': 0.20317308841552098, 'wp_1_0': -333.81838634484785, 'wp_1_1': 0.22871891487014384, 'wp_2_0': -35.972014273964511}, {}, {}, {'wm_1_2_0': -0.098475904735574632, 'wm_1_2_1': -6.5298014901415088e-07, 'wl_1': array([-0.21938336]), 'wl_2': array([ -1.17792422e-06]), 'wp_2_1': 0.076725693288236349, 'wp_1_0': -832.25265816464673, 'wp_1_1': 0.13048903181838342, 'wp_2_0': -542.69057541880818}, {'wm_1_2_0': -0.070707871151510754, 'wm_1_2_1': -1.4539026148453761e-06, 'wl_1': array([-0.41632912]), 'wl_2': array([ -1.72003570e-06]), 'wp_2_1': 0.98670934331059457, 'wp_1_0': -1.2045548134814041, 'wp_1_1': -1.3181768718353979, 'wp_2_0': -2.3111977019507047e-06}, {}, {'wm_1_2_0': -1.1045654284349922, 'wm_1_2_1': 1.813286468390625e-06, 'wl_1': array([-0.39588694]), 'wl_2': array([ -9.81054687e-07]), 'wp_2_1': 0.41380947602528195, 'wp_1_0': -31.806587329431387, 'wp_1_1': 0.57079970550486858, 'wp_2_0': -0.75433297278376943}, {}, {'wm_1_2_0': -0.41325964740224674, 'wm_1_2_1': -1.0450939566351188e-07, 'wl_1': array([-0.44083671]), 'wl_2': array([ -1.62869892e-06]), 'wp_2_1': 0.13151949065363516, 'wp_1_0': -4150.9551490994427, 'wp_1_1': 0.070769197743614176, 'wp_2_0': -446.24211176028859}, {'wm_1_2_0': -0.61032476019581461, 'wm_1_2_1': 5.7606264538801806e-07, 'wl_1': array([-0.41295567]), 'wl_2': array([ -1.12411196e-06]), 'wp_2_1': 0.30513231378179612, 'wp_1_0': -50.384835523541675, 'wp_1_1': 0.5230114821996521, 'wp_2_0': -9.24770454956907}, {}, {}, {}, {'wm_1_2_0': -0.31290263203957575, 'wm_1_2_1': -4.0264775122796882e-07, 'wl_1': array([-0.46880113]), 'wl_2': array([ -1.16743285e-06]), 'wp_2_1': 0.45958544795338874, 'wp_1_0': -2.8063756944165954, 'wp_1_1': 0.81878255840386227, 'wp_2_0': -0.2637169437770408}, {'wm_1_2_0': -0.16954987277099057, 'wm_1_2_1': -6.4973672319318219e-07, 'wl_1': array([-0.4057105]), 'wl_2': array([ -1.08107905e-06]), 'wp_2_1': 0.74854036497657406, 'wp_1_0': -0.23348122460194717, 'wp_1_1': 1.0558294279536087, 'wp_2_0': -0.00033559379841656677}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.23499667087289183, 'wm_1_2_1': -4.7867836126539991e-07, 'wl_1': array([-0.40673356]), 'wl_2': array([ -1.08799367e-06]), 'wp_2_1': 0.63764382818448928, 'wp_1_0': -0.83792482916782507, 'wp_1_1': 0.92725121835417224, 'wp_2_0': -0.0042681899115502835}, {}, {}, {}, {'wm_1_2_0': 0.059208452577246488, 'wm_1_2_1': -1.8389646038502033e-06, 'wl_1': array([-0.50993288]), 'wl_2': array([ -1.65426077e-06]), 'wp_2_1': 0.79365394903416275, 'wp_1_0': -91189.939314037591, 'wp_1_1': -0.20280333575924783, 'wp_2_0': -0.00018110017108652685}, {'wm_1_2_0': 0.059208452577245753, 'wm_1_2_1': -1.8389646038502014e-06, 'wl_1': array([-0.50993288]), 'wl_2': array([ -1.65426077e-06]), 'wp_2_1': 0.7936540952564487, 'wp_1_0': -91189.970218464077, 'wp_1_1': -0.20280336974193638, 'wp_2_0': -0.00018109956888428058}, {}, {}, {'wm_1_2_0': -0.65006039153042527, 'wm_1_2_1': 3.7445294432319565e-07, 'wl_1': array([-0.48424411]), 'wl_2': array([ -1.07154291e-06]), 'wp_2_1': 0.38315448296827231, 'wp_1_0': -37.342240378841907, 'wp_1_1': 0.57465208499373033, 'wp_2_0': -1.8255738861052448}, {}, {'wm_1_2_0': 0.4144280397467115, 'wm_1_2_1': -2.3035211616894036e-06, 'wl_1': array([-0.65386899]), 'wl_2': array([ -1.43385060e-06]), 'wp_2_1': 1.1449581663291413, 'wp_1_0': -0.093243568914895505, 'wp_1_1': 1.1908092302900295, 'wp_2_0': -4.8697915903541764e-08}, {}, {}, {}, {'wm_1_2_0': -1.3086116430451835, 'wm_1_2_1': 3.7023922869360943e-06, 'wl_1': array([-0.32822934]), 'wl_2': array([ -1.23819753e-06]), 'wp_2_1': 0.28143064812462715, 'wp_1_0': -305.77516677378776, 'wp_1_1': 0.31247491655151721, 'wp_2_0': -12.391465495489648}, {'wm_1_2_0': -1.3086116430451835, 'wm_1_2_1': 3.7023922869360943e-06, 'wl_1': array([-0.32822934]), 'wl_2': array([ -1.23819753e-06]), 'wp_2_1': 0.28143064812462715, 'wp_1_0': -305.77516677378776, 'wp_1_1': 0.31247491655151721, 'wp_2_0': -12.391465495489648}, {'wm_1_2_0': 0.17698926471723425, 'wm_1_2_1': -1.8290896280597881e-06, 'wl_1': array([-0.61418884]), 'wl_2': array([ -1.44017291e-06]), 'wp_2_1': 1.0669529400034887, 'wp_1_0': -0.0066958519220825024, 'wp_1_1': 1.4439630667307617, 'wp_2_0': -3.0307504159225528e-07}, {'wm_1_2_0': -0.34517375274127415, 'wm_1_2_1': -5.5033839374737792e-07, 'wl_1': array([-0.51274199]), 'wl_2': array([ -1.51392380e-06]), 'wp_2_1': 0.67873184756201432, 'wp_1_0': -0.22745925757545118, 'wp_1_1': 1.0843091137071268, 'wp_2_0': -0.0022346982809018142}, {}, {}, {}, {}, {}, {}, {}, {'wm_1_2_0': 0.64702010612885275, 'wm_1_2_1': -9.3116873083081924e-06, 'wl_1': array([-0.63989217]), 'wl_2': array([ -5.08606966e-06]), 'wp_2_1': 1.0373625278896663, 'wp_1_0': -93.203687053127055, 'wp_1_1': 0.49849462100824371, 'wp_2_0': -2.8621476981420725e-06}, {}, {'wm_1_2_0': 0.61963215944904559, 'wm_1_2_1': -9.2412157047970774e-06, 'wl_1': array([-0.64928257]), 'wl_2': array([ -5.13053029e-06]), 'wp_2_1': 1.0323571403989187, 'wp_1_0': -109.58645832431532, 'wp_1_1': 0.48039419619267149, 'wp_2_0': -3.145094906385813e-06}, {}, {}, {}, {}, {}, {'wm_1_2_0': 1.2540722841570935, 'wm_1_2_1': -1.5318098619464535e-05, 'wl_1': array([-1.30539569]), 'wl_2': array([ -8.35444132e-06]), 'wp_2_1': 1.2842784102476914, 'wp_1_0': -0.34910222232815824, 'wp_1_1': 1.1546103892706781, 'wp_2_0': -1.9913962122623501e-08}, {}, {'wm_1_2_0': 0.020912798326409365, 'wm_1_2_1': -1.2425513972918617e-06, 'wl_1': array([-0.318187]), 'wl_2': array([ -1.16615234e-06]), 'wp_2_1': 0.9834196498057437, 'wp_1_0': -0.0095238973397767414, 'wp_1_1': 1.362236134194128, 'wp_2_0': -1.6853083513730504e-06}, {'wm_1_2_0': -0.27754810806752911, 'wm_1_2_1': -9.0008554610222941e-07, 'wl_1': array([-0.49328671]), 'wl_2': array([ -1.92330111e-06]), 'wp_2_1': 0.38856925645083096, 'wp_1_0': -369.18408679435981, 'wp_1_1': 0.32862862888533989, 'wp_2_0': -1.6820806058349969}, {}, {'wm_1_2_0': -0.27872070480691774, 'wm_1_2_1': -7.2933552243429915e-07, 'wl_1': array([-0.45836482]), 'wl_2': array([ -1.75480204e-06]), 'wp_2_1': 0.43944426381056101, 'wp_1_0': -16.399173256131409, 'wp_1_1': 0.63594229143208547, 'wp_2_0': -0.48068478753651983}, {}, {}, {'wm_1_2_0': -0.37107162170652569, 'wm_1_2_1': -1.0768226457514814e-06, 'wl_1': array([-0.60212293]), 'wl_2': array([ -2.62895337e-06]), 'wp_2_1': 0.54912459835916916, 'wp_1_0': -0.10709971931448688, 'wp_1_1': 1.1753577541499187, 'wp_2_0': -0.060246926680850799}, {}, {'wm_1_2_0': -0.40923975142725877, 'wm_1_2_1': -6.9918684759592077e-07, 'wl_1': array([-0.56412092]), 'wl_2': array([ -2.38498644e-06]), 'wp_2_1': 0.56790277441733095, 'wp_1_0': -2.4241976114282826, 'wp_1_1': -1.1900895632284687, 'wp_2_0': -0.035520126783492437}, {}, {}, {'wm_1_2_0': 0.063377642544805851, 'wm_1_2_1': -2.8181010862501933e-06, 'wl_1': array([-0.54536659]), 'wl_2': array([ -2.52636996e-06]), 'wp_2_1': 1.013243469290698, 'wp_1_0': 2.4804611355953581, 'wp_1_1': -1.5023995361597555, 'wp_2_0': -1.8850877640948207e-06}, {}, {'wm_1_2_0': 0.063377642544805851, 'wm_1_2_1': -2.8181010862501933e-06, 'wl_1': array([-0.54536659]), 'wl_2': array([ -2.52636996e-06]), 'wp_2_1': 1.013243469290698, 'wp_1_0': 2.4804611355953581, 'wp_1_1': -1.5023995361597555, 'wp_2_0': -1.8850877640948207e-06}, {'wm_1_2_0': -0.38519800088838041, 'wm_1_2_1': -5.7598943462649105e-07, 'wl_1': array([-0.51889383]), 'wl_2': array([ -2.08388105e-06]), 'wp_2_1': 0.47308742299186435, 'wp_1_0': -0.24519396187306705, 'wp_1_1': 1.0763082916569129, 'wp_2_0': -0.26174942069727375}, {}, {'wm_1_2_0': -0.53728539213735471, 'wm_1_2_1': 2.4290001428504033e-07, 'wl_1': array([-0.46676272]), 'wl_2': array([ -1.34475834e-06]), 'wp_2_1': 0.23408769514028685, 'wp_1_0': -0.0055521627320111993, 'wp_1_1': 1.4383255026387984, 'wp_2_0': -56.514457877981116}, {}, {}, {'wm_1_2_0': -0.006084363391300582, 'wm_1_2_1': -1.4861716362911378e-06, 'wl_1': array([-0.52430205]), 'wl_2': array([ -1.50280943e-06]), 'wp_2_1': 1.1436352698822581, 'wp_1_0': -3.6457931445164312e-05, 'wp_1_1': 1.9475870754123159, 'wp_2_0': -5.5683126891827567e-08}, {}, {'wm_1_2_0': -0.37376164944700713, 'wm_1_2_1': -2.2534131958394345e-08, 'wl_1': array([-0.38035363]), 'wl_2': array([ -1.05897004e-06]), 'wp_2_1': 0.13741012477362358, 'wp_1_0': -4.3708434338217472, 'wp_1_1': 0.76023912883070499, 'wp_2_0': -447.62933082018833}, {'wm_1_2_0': -0.45175055555988258, 'wm_1_2_1': -3.3594384976953104e-07, 'wl_1': array([-0.55249743]), 'wl_2': array([ -1.74326122e-06]), 'wp_2_1': 0.29369136011807345, 'wp_1_0': -195.93368060490789, 'wp_1_1': 0.42469990571611077, 'wp_2_0': -18.531602926489931}, {}, {'wm_1_2_0': -0.45459668010148735, 'wm_1_2_1': -2.8195294188814902e-07, 'wl_1': array([-0.5389893]), 'wl_2': array([ -1.68485677e-06]), 'wp_2_1': 0.27936616842069506, 'wp_1_0': -177.30787970703315, 'wp_1_1': 0.43195641243790561, 'wp_2_0': -25.081082656344897}, {}, {}, {'wm_1_2_0': -1.345174681631687, 'wm_1_2_1': 5.6805693197630112e-06, 'wl_1': array([-0.60037365]), 'wl_2': array([ -4.45022147e-06]), 'wp_2_1': 0.35473677095106837, 'wp_1_0': -37.080131299306068, 'wp_1_1': 0.59447919576162189, 'wp_2_0': -6.4793866647576941}, {}, {'wm_1_2_0': -1.345174681631687, 'wm_1_2_1': 5.6805693197630112e-06, 'wl_1': array([-0.60037365]), 'wl_2': array([ -4.45022147e-06]), 'wp_2_1': 0.35473677095106837, 'wp_1_0': -37.080131299306068, 'wp_1_1': 0.59447919576162189, 'wp_2_0': -6.4793866647576941}, {'wm_1_2_0': -0.41976716653187068, 'wm_1_2_1': -3.8314681772787922e-07, 'wl_1': array([-0.53745683]), 'wl_2': array([ -1.62829266e-06]), 'wp_2_1': 0.33882952738423122, 'wp_1_0': -1.7444172303289678, 'wp_1_1': 0.88430667549726394, 'wp_2_0': -6.1510891810735178}, {}, {}, {}, {}, {}, {}, {}, {'wm_1_2_0': -0.55089445568904827, 'wm_1_2_1': 3.8789348322054292e-07, 'wl_1': array([-0.43415654]), 'wl_2': array([ -1.28293456e-06]), 'wp_2_1': 0.062176101806936848, 'wp_1_0': -0.21579820723659168, 'wp_1_1': 1.0658747581920116, 'wp_2_0': -4007.2973329406509}, {}, {'wm_1_2_0': -0.48285428484449039, 'wm_1_2_1': 1.9308287503599136e-07, 'wl_1': array([-0.42682569]), 'wl_2': array([ -1.30169515e-06]), 'wp_2_1': 0.10809462997268678, 'wp_1_0': -0.016170214680000738, 'wp_1_1': 1.3086950680056213, 'wp_2_0': -1353.9084239631297}, {}, {'wm_1_2_0': -0.13353017429477607, 'wm_1_2_1': -1.8896157670468377e-06, 'wl_1': array([-0.4878543]), 'wl_2': array([ -2.57656879e-06]), 'wp_2_1': 0.79775983614897183, 'wp_1_0': -1.0128377024680527e-06, 'wp_1_1': 2.2479323872355055, 'wp_2_0': -0.00025384420890635969}, {}, {}, {'wm_1_2_0': -0.68358003823677327, 'wm_1_2_1': 1.1895586801151777e-06, 'wl_1': array([-0.34301617]), 'wl_2': array([ -9.72139943e-07]), 'wp_2_1': -0.24647691777873487, 'wp_1_0': -0.52466503703228384, 'wp_1_1': 0.95986235227924399, 'wp_2_0': -3665104.0047176196}, {'wm_1_2_0': -0.44327832864860256, 'wm_1_2_1': -3.6244142567077146e-08, 'wl_1': array([-0.4538319]), 'wl_2': array([ -1.41355348e-06]), 'wp_2_1': 0.098411446291105015, 'wp_1_0': -1458.086953968912, 'wp_1_1': 0.23672310782537559, 'wp_2_0': -1834.8513555482045}, {'wm_1_2_0': -0.46619631474067275, 'wm_1_2_1': -1.42839640318229e-07, 'wl_1': array([-0.50689947]), 'wl_2': array([ -1.61195271e-06]), 'wp_2_1': 0.36608220073389336, 'wp_1_0': -26.355399854102671, 'wp_1_1': 0.61460563781708277, 'wp_2_0': -3.3561478306496539}, {}, {'wm_1_2_0': -1.249477016456541, 'wm_1_2_1': 1.2364817086686375e-06, 'wl_1': array([-1.00316788]), 'wl_2': array([ -4.55753898e-06]), 'wp_2_1': 0.5553186446395465, 'wp_1_0': -1.7505412555743424e-07, 'wp_1_1': 2.6183210954061651, 'wp_2_0': -0.076784669960463015}, {'wm_1_2_0': -0.7410548200289343, 'wm_1_2_1': 8.3019385033395009e-07, 'wl_1': array([-0.57626116]), 'wl_2': array([ -2.56210469e-06]), 'wp_2_1': 0.48985104753820219, 'wp_1_0': -5.0025391040789229, 'wp_1_1': 0.7728332262001455, 'wp_2_0': -0.17475487003012571}, {}, {'wm_1_2_0': -1.0052278851192298, 'wm_1_2_1': 1.0030670799867145e-06, 'wl_1': array([-0.80585687]), 'wl_2': array([ -3.64042453e-06]), 'wp_2_1': 0.57942589662509614, 'wp_1_0': -0.28647764364926909, 'wp_1_1': 1.10894616481532, 'wp_2_0': -0.035796625021743751}, {'wm_1_2_0': 0.67700701341247171, 'wm_1_2_1': -8.7389574894348997e-06, 'wl_1': array([-0.88859078]), 'wl_2': array([ -5.05116972e-06]), 'wp_2_1': 0.95206754815498074, 'wp_1_0': -136.94074270498001, 'wp_1_1': 0.46116199673111907, 'wp_2_0': -1.4132216695589342e-05}, {'wm_1_2_0': -0.80101295539215811, 'wm_1_2_1': 1.0351072716928705e-06, 'wl_1': array([-0.64791275]), 'wl_2': array([ -3.61236618e-06]), 'wp_2_1': 0.3537350035676689, 'wp_1_0': -2.6975175304715631, 'wp_1_1': 0.84941944299201388, 'wp_2_0': -4.1925123873755306}, {'wm_1_2_0': -0.95055585890989269, 'wm_1_2_1': 1.9929709013320145e-06, 'wl_1': array([-0.56374999]), 'wl_2': array([ -2.51423431e-06]), 'wp_2_1': 0.14486921551848186, 'wp_1_0': -21.865482879022871, 'wp_1_1': 0.60962078945329723, 'wp_2_0': -276.85369316882287}, {}, {'wm_1_2_0': -0.85655731798784129, 'wm_1_2_1': 1.4205993671183747e-06, 'wl_1': array([-0.6170203]), 'wl_2': array([ -3.04449665e-06]), 'wp_2_1': 0.28119321164495642, 'wp_1_0': -4.9732022236642495, 'wp_1_1': 0.77863410851370718, 'wp_2_0': -17.432434834488561}, {}, {'wm_1_2_0': -0.61382839953974688, 'wm_1_2_1': 5.4301122634282281e-07, 'wl_1': array([-0.55269337]), 'wl_2': array([ -3.73354645e-06]), 'wp_2_1': 0.17063501222823274, 'wp_1_0': -29.368299765724714, 'wp_1_1': 0.57959636727218433, 'wp_2_0': -189.37344323225844}, {'wm_1_2_0': -1.2857667796081365, 'wm_1_2_1': 5.6833133469593667e-06, 'wl_1': array([-0.56577512]), 'wl_2': array([ -3.75479561e-06]), 'wp_2_1': -0.05820464242410623, 'wp_1_0': -40037.096811282237, 'wp_1_1': -0.22358027174463085, 'wp_2_0': -16984.591530179918}, {}, {'wm_1_2_0': -0.67929689612816524, 'wm_1_2_1': 1.0611752126138882e-06, 'wl_1': array([-0.5560197]), 'wl_2': array([ -3.73921884e-06]), 'wp_2_1': 0.15458703334793714, 'wp_1_0': -151.43539800981577, 'wp_1_1': 0.4011223428541924, 'wp_2_0': -241.63887815409421}, {'wm_1_2_0': -0.81031790077631738, 'wm_1_2_1': 6.9405864590083761e-07, 'wl_1': array([-0.68703245]), 'wl_2': array([ -3.33997872e-06]), 'wp_2_1': 0.42583041775145375, 'wp_1_0': -0.66516811445547863, 'wp_1_1': 1.0036332368912859, 'wp_2_0': -0.87430896962656557}, {}, {'wm_1_2_0': -0.66643615919266708, 'wm_1_2_1': -6.8912602316084145e-07, 'wl_1': array([-0.84729407]), 'wl_2': array([ -2.99009046e-06]), 'wp_2_1': 0.74250712418617648, 'wp_1_0': 2.2108648476355954, 'wp_1_1': -2.1155916260614922, 'wp_2_0': -0.0010426258145449637}, {'wm_1_2_0': -0.06653263900646196, 'wm_1_2_1': -1.3725573615480509e-06, 'wl_1': array([-0.43012596]), 'wl_2': array([ -1.60855203e-06]), 'wp_2_1': 0.94334987396461845, 'wp_1_0': -0.072869971031340949, 'wp_1_1': 1.1761563347887862, 'wp_2_0': -5.8164684826464216e-06}, {'wm_1_2_0': -0.081895198388826695, 'wm_1_2_1': -2.011957416022875e-06, 'wl_1': array([-0.516146]), 'wl_2': array([ -2.37570547e-06]), 'wp_2_1': 0.81077603362111927, 'wp_1_0': -0.051541485451120028, 'wp_1_1': 1.2279846325814454, 'wp_2_0': -0.00016748124656821331}, {'wm_1_2_0': -0.30214265713510158, 'wm_1_2_1': -1.0298837470807355e-06, 'wl_1': array([-0.57281423]), 'wl_2': array([ -2.09631230e-06]), 'wp_2_1': 0.91363529621193029, 'wp_1_0': 1.8429865930774612, 'wp_1_1': -1.628009158680632, 'wp_2_0': -1.4895518934324848e-05}, {'wm_1_2_0': -1.0645673217631433, 'wm_1_2_1': 5.9770621590919543e-06, 'wl_1': array([-0.2826778]), 'wl_2': array([ -2.00243163e-06]), 'wp_2_1': 0.40374350023318728, 'wp_1_0': -0.1656724558319019, 'wp_1_1': 1.0554654156708829, 'wp_2_0': -0.70111851916514045}, {'wm_1_2_0': -0.23038614300084351, 'wm_1_2_1': -1.6374048174444816e-06, 'wl_1': array([-0.62114472]), 'wl_2': array([ -2.51979723e-06]), 'wp_2_1': 1.2694807074840122, 'wp_1_0': 1.1027827697094481, 'wp_1_1': -2.4153090632621903, 'wp_2_0': -5.6538596973758113e-09}, {'wm_1_2_0': -0.37612693669665187, 'wm_1_2_1': -3.8646883906264726e-07, 'wl_1': array([-0.46990685]), 'wl_2': array([ -1.77819247e-06]), 'wp_2_1': 0.5189084138637704, 'wp_1_0': -3.570436819529645, 'wp_1_1': 0.79765896495793476, 'wp_2_0': -0.09310875855690251}, {'wm_1_2_0': -0.86477776282270136, 'wm_1_2_1': 1.0523613586002612e-06, 'wl_1': array([-0.64876675]), 'wl_2': array([ -2.82125075e-06]), 'wp_2_1': 0.30060692676030348, 'wp_1_0': -6.3412151644034586e-07, 'wp_1_1': 2.3713969397730437, 'wp_2_0': -18.262480591250227}, {'wm_1_2_0': -0.34873572236785938, 'wm_1_2_1': -7.8554520965831753e-07, 'wl_1': array([-0.53705651]), 'wl_2': array([ -2.10041818e-06]), 'wp_2_1': 0.80398602464321001, 'wp_1_0': 0.73594932876473962, 'wp_1_1': -1.6294299705558355, 'wp_2_0': -0.00017650408486590921}, {}, {'wm_1_2_0': -0.70494769520823086, 'wm_1_2_1': 1.595194585497853e-07, 'wl_1': array([-0.67273993]), 'wl_2': array([ -3.05879776e-06]), 'wp_2_1': 0.55364163383401843, 'wp_1_0': -0.0015960283675122684, 'wp_1_1': 1.6016790132398395, 'wp_2_0': -0.067471010112092542}, {'wm_1_2_0': -0.47044823442799499, 'wm_1_2_1': -2.7449329196597663e-08, 'wl_1': array([-0.47663142]), 'wl_2': array([ -1.93412707e-06]), 'wp_2_1': 0.21084873047172376, 'wp_1_0': -185.15048347426173, 'wp_1_1': 0.40629023379347801, 'wp_2_0': -97.45715138469599}, {}, {'wm_1_2_0': -0.61070140555457919, 'wm_1_2_1': 2.567490600341467e-07, 'wl_1': array([-0.55548091]), 'wl_2': array([ -2.33497103e-06]), 'wp_2_1': 0.35112309453008267, 'wp_1_0': -2.9738010602483049, 'wp_1_1': 0.83295874448389018, 'wp_2_0': -4.9666460912535131}, {'wm_1_2_0': -0.35168375956986103, 'wm_1_2_1': -8.1636895575548358e-07, 'wl_1': array([-0.55386195]), 'wl_2': array([ -2.11189681e-06]), 'wp_2_1': 0.79976204978033261, 'wp_1_0': -0.86728894884854579, 'wp_1_1': -1.3903371875224968, 'wp_2_0': -0.00019665187068143564}, {}, {'wm_1_2_0': -0.69242427424456165, 'wm_1_2_1': 1.8449915161583378e-07, 'wl_1': array([-0.6325744]), 'wl_2': array([ -1.82859964e-06]), 'wp_2_1': 0.53951460405508667, 'wp_1_0': -0.0081307728489219099, 'wp_1_1': 1.4185990163414841, 'wp_2_0': -0.079281547327226559}, {'wm_1_2_0': -0.28465278595994403, 'wm_1_2_1': -3.9417998806589234e-07, 'wl_1': array([-0.43465681]), 'wl_2': array([ -1.10374798e-06]), 'wp_2_1': 0.60549703599273297, 'wp_1_0': -0.31735112428634427, 'wp_1_1': 1.0302428091546674, 'wp_2_0': -0.010963793073575636}, {'wm_1_2_0': -0.38143279378088762, 'wm_1_2_1': -5.0514921122268998e-07, 'wl_1': array([-0.51916752]), 'wl_2': array([ -1.81281636e-06]), 'wp_2_1': 0.43145072949202362, 'wp_1_0': -1.1578863944172493, 'wp_1_1': 0.92261797088548736, 'wp_2_0': -0.84681075801152494}, {'wm_1_2_0': -0.47759655760589137, 'wm_1_2_1': -1.139367899397804e-08, 'wl_1': array([-0.48174712]), 'wl_2': array([ -1.24569916e-06]), 'wp_2_1': 0.46808208968046439, 'wp_1_0': -0.090014303166739473, 'wp_1_1': 1.1612826491140447, 'wp_2_0': -0.29898772979182825}, {}, {'wm_1_2_0': -0.36810802014516519, 'wm_1_2_1': -6.9545224791068e-07, 'wl_1': array([-0.59554015]), 'wl_2': array([ -1.77387351e-06]), 'wp_2_1': 0.72930578578009264, 'wp_1_0': -0.040720586298676448, 'wp_1_1': 1.2577076313530213, 'wp_2_0': -0.00093693691394960499}, {'wm_1_2_0': -0.41865789787803503, 'wm_1_2_1': -1.6729869192440529e-07, 'wl_1': array([-0.48110027]), 'wl_2': array([ -1.22723793e-06]), 'wp_2_1': 0.34959470029294748, 'wp_1_0': -10.523911211871388, 'wp_1_1': 0.70421145843320554, 'wp_2_0': -4.7877023721966889}, {'wm_1_2_0': 0.0411760540210983, 'wm_1_2_1': -1.5095711336666993e-06, 'wl_1': array([-0.42269826]), 'wl_2': array([ -1.38211896e-06]), 'wp_2_1': 1.2657806307687791, 'wp_1_0': -0.14782249726409702, 'wp_1_1': 1.100284165255816, 'wp_2_0': -2.9043610935358822e-09}, {'wm_1_2_0': -0.43026070123511595, 'wm_1_2_1': -1.6891984240696793e-07, 'wl_1': array([-0.49210768]), 'wl_2': array([ -1.27824266e-06]), 'wp_2_1': 0.37439526105368059, 'wp_1_0': -5.6898627908134474, 'wp_1_1': 0.76529803422488085, 'wp_2_0': -2.760865647907901}, {}, {}, {'wm_1_2_0': -0.35933981270481319, 'wm_1_2_1': -2.7015495788981732e-07, 'wl_1': array([-0.4287435]), 'wl_2': array([ -1.49087953e-06]), 'wp_2_1': 0.3532601506996832, 'wp_1_0': -0.018363656230860045, 'wp_1_1': 1.3017600977194139, 'wp_2_0': -4.4455582173401131}, {'wm_1_2_0': -0.55467845172200192, 'wm_1_2_1': 1.1851800228495881e-06, 'wl_1': array([-0.26110924]), 'wl_2': array([ -9.04517972e-07]), 'wp_2_1': 0.17626463518577165, 'wp_1_0': -499.63150430474394, 'wp_1_1': 0.290043305088095, 'wp_2_0': -180.5873117649223}, {'wm_1_2_0': -0.35148898225811831, 'wm_1_2_1': -2.5310597835640514e-07, 'wl_1': array([-0.41638383]), 'wl_2': array([ -1.45808174e-06]), 'wp_2_1': 0.36260062991209863, 'wp_1_0': -0.97648971539463103, 'wp_1_1': 0.91839063111047226, 'wp_2_0': -3.5076756840360552}, {'wm_1_2_0': -0.41618689261141301, 'wm_1_2_1': -1.9183002104045759e-07, 'wl_1': array([-0.48479837]), 'wl_2': array([ -1.27972941e-06]), 'wp_2_1': 0.40768365391485983, 'wp_1_0': -1.4511230596084237, 'wp_1_1': 0.89483149767340919, 'wp_2_0': -1.260041748266578}, {}, {'wm_1_2_0': -0.8234875037227446, 'wm_1_2_1': 6.224172806682503e-07, 'wl_1': array([-0.58588954]), 'wl_2': array([ -1.41379709e-06]), 'wp_2_1': 0.089981887025157151, 'wp_1_0': -16.96839596692389, 'wp_1_1': 0.68683863262719813, 'wp_2_0': -3184.1272890692344}, {'wm_1_2_0': -0.44693140626778416, 'wm_1_2_1': 5.3889572097215021e-09, 'wl_1': array([-0.44460874]), 'wl_2': array([ -9.82993697e-07]), 'wp_2_1': 0.36381054284164382, 'wp_1_0': -0.23832080122530153, 'wp_1_1': 1.0582892904486998, 'wp_2_0': -3.5532315948216247}, {}, {'wm_1_2_0': -0.49178868349249066, 'wm_1_2_1': 8.8778135539228072e-08, 'wl_1': array([-0.4538098]), 'wl_2': array([ -1.00552314e-06]), 'wp_2_1': 0.32228763400694771, 'wp_1_0': -0.25622401437444819, 'wp_1_1': 1.0534149774067909, 'wp_2_0': -9.7064817736420803}, {}, {}, {}, {'wm_1_2_0': -0.36519834597861389, 'wm_1_2_1': -5.2343904107360049e-07, 'wl_1': array([-0.52791901]), 'wl_2': array([ -1.65726735e-06]), 'wp_2_1': 0.68625577184535269, 'wp_1_0': -77.953668580358595, 'wp_1_1': 0.53618162023490623, 'wp_2_0': -0.0025905845769142984}, {}, {}, {'wm_1_2_0': 0.10369666039775711, 'wm_1_2_1': -3.3261155699956841e-06, 'wl_1': array([-0.84260913]), 'wl_2': array([ -2.96933471e-06]), 'wp_2_1': 0.99222738009088629, 'wp_1_0': -0.92905795042310546, 'wp_1_1': 0.99089524198451762, 'wp_2_0': -3.5596907033537475e-06}, {'wm_1_2_0': -0.482964905535889, 'wm_1_2_1': 6.2154723037358472e-08, 'wl_1': array([-0.45949152]), 'wl_2': array([ -1.08348622e-06]), 'wp_2_1': 0.2852004481049632, 'wp_1_0': -0.41910048073888218, 'wp_1_1': 1.0086350371777819, 'wp_2_0': -23.740409415333499}, {'wm_1_2_0': 0.20419669136235452, 'wm_1_2_1': -2.3370974776974707e-06, 'wl_1': array([-0.47166636]), 'wl_2': array([ -1.64069700e-06]), 'wp_2_1': 0.72598279501869067, 'wp_1_0': -2.4244003943316175, 'wp_1_1': 0.85064375246967039, 'wp_2_0': -0.0010267862423523906}, {'wm_1_2_0': -0.65662601252420538, 'wm_1_2_1': 3.3820655778044834e-07, 'wl_1': array([-0.53670302]), 'wl_2': array([ -1.32288321e-06]), 'wp_2_1': 0.26538809653788947, 'wp_1_0': -0.027168297804177441, 'wp_1_1': 1.2791428128859352, 'wp_2_0': -44.867438846859557}, {'wm_1_2_0': 1.2964764456391762, 'wm_1_2_1': -4.3577596552273935e-06, 'wl_1': array([-0.59457494]), 'wl_2': array([ -1.73446775e-06]), 'wp_2_1': 1.724907902673005, 'wp_1_0': 22.440570784839675, 'wp_1_1': -8.0540989992607503, 'wp_2_0': -3.7468279802128521e-14}, {'wm_1_2_0': 0.33804040725760709, 'wm_1_2_1': -2.4041695665170367e-06, 'wl_1': array([-0.54637085]), 'wl_2': array([ -1.60609047e-06]), 'wp_2_1': 1.6228634067053749, 'wp_1_0': -1.1212529886516702, 'wp_1_1': -1.2396465671007542, 'wp_2_0': -5.2100079475224539e-13}, {}, {'wm_1_2_0': -0.92067052999940757, 'wm_1_2_1': 2.4614088285496838e-06, 'wl_1': array([-0.42361912]), 'wl_2': array([ -1.93377046e-06]), 'wp_2_1': 0.36896250363812605, 'wp_1_0': -25.681417698600526, 'wp_1_1': 0.57987140029423212, 'wp_2_0': -2.2236579833488919}, {'wm_1_2_0': -0.22147571945302974, 'wm_1_2_1': -4.7702033912778459e-07, 'wl_1': array([-0.30715652]), 'wl_2': array([ -1.61030105e-06]), 'wp_2_1': 0.12059015871606449, 'wp_1_0': -514.70274612609944, 'wp_1_1': 0.24285840662022179, 'wp_2_0': -387.38708171468789}, {}, {'wm_1_2_0': -0.33027737145699515, 'wm_1_2_1': -7.7409958717579019e-08, 'wl_1': array([-0.34471645]), 'wl_2': array([ -1.72481374e-06]), 'wp_2_1': 0.26878115431061417, 'wp_1_0': -113.03522521296881, 'wp_1_1': 0.40924837961511329, 'wp_2_0': -16.859667406591782}, {}, {'wm_1_2_0': -0.47733419478385747, 'wm_1_2_1': -4.3170586004387023e-07, 'wl_1': array([-0.52675611]), 'wl_2': array([ -4.02686478e-06]), 'wp_2_1': 0.62315555751620133, 'wp_1_0': -1.7360869164543495, 'wp_1_1': 0.87366884757642504, 'wp_2_0': -0.012677418678840476}, {'wm_1_2_0': -1.6614622669092238, 'wm_1_2_1': 5.8900530109521211e-06, 'wl_1': array([-0.73551683]), 'wl_2': array([ -3.80876500e-06]), 'wp_2_1': 0.10676151150027312, 'wp_1_0': -125.48179125723962, 'wp_1_1': 0.4774202518912144, 'wp_2_0': -1166.5750264381329}, {'wm_1_2_0': -0.51837761945320593, 'wm_1_2_1': 8.9663060139433054e-07, 'wl_1': array([-0.36716908]), 'wl_2': array([ -1.88312454e-06]), 'wp_2_1': 1.1787139247847331, 'wp_1_0': -0.64640207414565087, 'wp_1_1': 0.94248204385164969, 'wp_2_0': -3.8469389180113291e-08}, {'wm_1_2_0': -0.89686874895634039, 'wm_1_2_1': 2.1000652992016392e-06, 'wl_1': array([-0.59150219]), 'wl_2': array([ -3.34013924e-06]), 'wp_2_1': 0.39383321203261229, 'wp_1_0': -5.6500707819055691, 'wp_1_1': 0.76912853668019576, 'wp_2_0': -1.8307212679083906}, {}, {'wm_1_2_0': -0.0015059538021779202, 'wm_1_2_1': -5.4259839501239944e-06, 'wl_1': array([-0.32609246]), 'wl_2': array([ -5.44958976e-06]), 'wp_2_1': 1.2786138333839889, 'wp_1_0': -12.46799814643019, 'wp_1_1': 0.64077058088239458, 'wp_2_0': -1.5292399202038121e-08}, {'wm_1_2_0': -0.52857421540757177, 'wm_1_2_1': 1.5751707570128233e-06, 'wl_1': array([-0.31533471]), 'wl_2': array([ -1.89046971e-06]), 'wp_2_1': -0.053057047446810009, 'wp_1_0': -6731.2032620389446, 'wp_1_1': -0.031660855849751562, 'wp_2_0': -15237.304424362737}, {'wm_1_2_0': -0.79474543280905441, 'wm_1_2_1': 2.2013855343402193e-06, 'wl_1': array([-0.41710239]), 'wl_2': array([ -2.37036980e-06]), 'wp_2_1': 0.5406968212259301, 'wp_1_0': -7.7004704170623191, 'wp_1_1': 0.70581525384737021, 'wp_2_0': -0.058404838733107596}, {'wm_1_2_0': -0.32811406574819024, 'wm_1_2_1': -1.3703390270835277e-07, 'wl_1': array([-0.34300724]), 'wl_2': array([ -2.52229615e-06]), 'wp_2_1': 0.23477074427285372, 'wp_1_0': -92.161683989150546, 'wp_1_1': 0.43593437076465036, 'wp_2_0': -41.877291861429775}, {'wm_1_2_0': -0.72322093830944956, 'wm_1_2_1': 1.4859414750206238e-06, 'wl_1': array([-0.49161074]), 'wl_2': array([ -2.59526549e-06]), 'wp_2_1': 0.30799372374211137, 'wp_1_0': -16.787397901966095, 'wp_1_1': 0.63923182035934301, 'wp_2_0': -9.8553588650949067}, {}, {'wm_1_2_0': -0.39431232971112423, 'wm_1_2_1': -5.4574629274050958e-07, 'wl_1': array([-0.53293001]), 'wl_2': array([ -1.97643679e-06]), 'wp_2_1': 0.61132214102348703, 'wp_1_0': 3.4743153065181183, 'wp_1_1': -1.3833894696708722, 'wp_2_0': -0.014383172572984384}, {'wm_1_2_0': -0.26878291127936804, 'wm_1_2_1': -2.3753215177871022e-07, 'wl_1': array([-0.34065331]), 'wl_2': array([ -1.05538268e-06]), 'wp_2_1': 0.93709311723710031, 'wp_1_0': 8.4296984140684224, 'wp_1_1': -1.9493535809004314, 'wp_2_0': -4.5178251950253621e-06}, {'wm_1_2_0': -0.71337642482678043, 'wm_1_2_1': 1.1199459537924694e-06, 'wl_1': array([-0.37898876]), 'wl_2': array([ -1.21955456e-06]), 'wp_2_1': 0.46002941254888835, 'wp_1_0': -2.2880416027240269, 'wp_1_1': 0.82531950395921461, 'wp_2_0': -0.28949851335692756}, {'wm_1_2_0': -0.33843318892753355, 'wm_1_2_1': -9.0656692886091129e-08, 'wl_1': array([-0.36536096]), 'wl_2': array([ -1.14498427e-06]), 'wp_2_1': 0.70282308666443993, 'wp_1_0': 4.8014579609037256, 'wp_1_1': -1.7204943694328692, 'wp_2_0': -0.0010827585145394495}, {}, {'wm_1_2_0': -0.3693118987142151, 'wm_1_2_1': -6.171532114527246e-07, 'wl_1': array([-0.49692537]), 'wl_2': array([ -2.17105247e-06]), 'wp_2_1': 0.53574443208611022, 'wp_1_0': -0.0019396306558856033, 'wp_1_1': 1.5381633404540949, 'wp_2_0': -0.084832918046266692}, {'wm_1_2_0': -0.42650562674207321, 'wm_1_2_1': 1.1776214885768027e-07, 'wl_1': array([-0.40102826]), 'wl_2': array([ -1.64312518e-06]), 'wp_2_1': 0.3106576115669229, 'wp_1_0': -1.0252088238623658, 'wp_1_1': 0.90890093529488358, 'wp_2_0': -10.414043176969745}, {'wm_1_2_0': -0.48642341296145059, 'wm_1_2_1': 3.9505360679342851e-07, 'wl_1': array([-0.38554553]), 'wl_2': array([ -1.35963804e-06]), 'wp_2_1': 0.58534566441645397, 'wp_1_0': -0.0023414039261424155, 'wp_1_1': 1.490443117102495, 'wp_2_0': -0.018523144770126319}, {'wm_1_2_0': -0.43173503748809844, 'wm_1_2_1': 1.1522487356448461e-07, 'wl_1': array([-0.40632718]), 'wl_2': array([ -1.63295095e-06]), 'wp_2_1': 0.35649509706453164, 'wp_1_0': -0.30908163302801034, 'wp_1_1': 1.0265342309838696, 'wp_2_0': -3.7441635149734367}, {}, {'wm_1_2_0': 1.2069442167675433, 'wm_1_2_1': -1.1211861717555647e-05, 'wl_1': array([-0.51030519]), 'wl_2': array([ -3.34736259e-06]), 'wp_2_1': 1.4503830099542594, 'wp_1_0': -0.040324004817516156, 'wp_1_1': 1.2500547842634187, 'wp_2_0': -1.5963240390203148e-10}, {'wm_1_2_0': -0.44878278631118729, 'wm_1_2_1': 2.6331753457721802e-07, 'wl_1': array([-0.40510945]), 'wl_2': array([ -2.29686025e-06]), 'wp_2_1': 0.51486078227449483, 'wp_1_0': -0.15429164743043788, 'wp_1_1': 1.0942486936993212, 'wp_2_0': -0.11551776419544607}, {}, {'wm_1_2_0': -0.47224292485423797, 'wm_1_2_1': 3.2125102277433094e-07, 'wl_1': array([-0.41951949]), 'wl_2': array([ -2.41633576e-06]), 'wp_2_1': 0.48307561951505873, 'wp_1_0': -0.32545503158443517, 'wp_1_1': 1.0248233465923513, 'wp_2_0': -0.24338885427887419}, {'wm_1_2_0': -0.42973631088408482, 'wm_1_2_1': 1.3762525921160358e-07, 'wl_1': array([-0.39733632]), 'wl_2': array([ -1.47667506e-06]), 'wp_2_1': 0.36193656892199877, 'wp_1_0': -0.033815460150889397, 'wp_1_1': 1.2388304749670997, 'wp_2_0': -3.1412488883065119}, {}, {}, {'wm_1_2_0': -0.44683932061821219, 'wm_1_2_1': 4.409643715824545e-07, 'wl_1': array([-0.30068293]), 'wl_2': array([ -7.82329893e-07]), 'wp_2_1': 0.050123635560369903, 'wp_1_0': -51.903998929036391, 'wp_1_1': 0.51766597043714024, 'wp_2_0': -3800.8697307224111}, {'wm_1_2_0': 0.47201660262386591, 'wm_1_2_1': -2.7194645656834587e-06, 'wl_1': array([-0.51328152]), 'wl_2': array([ -1.43049512e-06]), 'wp_2_1': 1.2368651153912298, 'wp_1_0': -0.0078008407691444008, 'wp_1_1': 1.3891777235737917, 'wp_2_0': -5.3530981875465104e-09}, {'wm_1_2_0': -0.50093992156447731, 'wm_1_2_1': 5.3656990213340997e-07, 'wl_1': array([-0.32332968]), 'wl_2': array([ -8.40429147e-07]), 'wp_2_1': 0.075156156232471405, 'wp_1_0': -17.156450349709875, 'wp_1_1': 0.6283929951435766, 'wp_2_0': -2274.1158352712505}, {}, {'wm_1_2_0': -0.47089136645847246, 'wm_1_2_1': -2.2834966013162009e-07, 'wl_1': array([-0.50716582]), 'wl_2': array([ -2.88314395e-06]), 'wp_2_1': 0.13131096546777549, 'wp_1_0': -2200.5712581282969, 'wp_1_1': 0.20553694477489742, 'wp_2_0': -998.8298317008298}, {'wm_1_2_0': -0.45090977466635451, 'wm_1_2_1': 2.6358772323379459e-07, 'wl_1': array([-0.37034695]), 'wl_2': array([ -1.07005463e-06]), 'wp_2_1': 0.1283461852934239, 'wp_1_0': -1.425504391143013, 'wp_1_1': 0.87306190811745665, 'wp_2_0': -747.42756570645702}, {'wm_1_2_0': -0.28650056792308326, 'wm_1_2_1': -4.1323413519913826e-07, 'wl_1': array([-0.43363237]), 'wl_2': array([ -1.19187490e-06]), 'wp_2_1': 1.0950740204833069, 'wp_1_0': 6.2838715029245593, 'wp_1_1': -1.6084958407138252, 'wp_2_0': -1.2578930644996554e-07}, {'wm_1_2_0': -0.45561769791010898, 'wm_1_2_1': 2.601438930218375e-07, 'wl_1': array([-0.37632435]), 'wl_2': array([ -1.08829292e-06]), 'wp_2_1': 0.14899385142952709, 'wp_1_0': -0.35704039467439352, 'wp_1_1': 1.0049722399879057, 'wp_2_0': -470.77846189635812}, {}, {'wm_1_2_0': -0.32143429192082079, 'wm_1_2_1': -1.2359155558459385e-06, 'wl_1': array([-0.49259786]), 'wl_2': array([ -3.51803798e-06]), 'wp_2_1': 0.33850752087965352, 'wp_1_0': -420.60824863741436, 'wp_1_1': 0.36336276658735489, 'wp_2_0': -9.9880988554272996}, {'wm_1_2_0': -0.5849660806274658, 'wm_1_2_1': 5.3974365856681282e-07, 'wl_1': array([-0.44714703]), 'wl_2': array([ -1.47500339e-06]), 'wp_2_1': 0.21528734271099847, 'wp_1_0': 2.7031816443676702, 'wp_1_1': -1.5971649346092369, 'wp_2_0': -125.97072367213713}, {}, {'wm_1_2_0': -0.57335879666031642, 'wm_1_2_1': 5.021453245895054e-07, 'wl_1': array([-0.45404407]), 'wl_2': array([ -1.56684504e-06]), 'wp_2_1': 0.17088878028272211, 'wp_1_0': -0.00061508261543391724, 'wp_1_1': 1.6195223165762651, 'wp_2_0': -360.09738859335988}, {'wm_1_2_0': -0.49142589334403303, 'wm_1_2_1': 3.8866905496903508e-07, 'wl_1': array([-0.37363798]), 'wl_2': array([ -1.06274855e-06]), 'wp_2_1': 0.11775891414622824, 'wp_1_0': -1.691823567811894, 'wp_1_1': 0.85805018192456395, 'wp_2_0': -967.03364765898573}, {}, {}, {'wm_1_2_0': -0.18930720585178465, 'wm_1_2_1': -5.9700277128738404e-07, 'wl_1': array([-0.32961865]), 'wl_2': array([ -1.31073165e-06]), 'wp_2_1': 0.7173176524562842, 'wp_1_0': -0.35340735809009116, 'wp_1_1': 0.99357388366696187, 'wp_2_0': -0.00094986885723584826}, {}, {'wm_1_2_0': -0.18743708371683851, 'wm_1_2_1': -6.7829278078515454e-07, 'wl_1': array([-0.3479348]), 'wl_2': array([ -1.37994103e-06]), 'wp_2_1': 0.73517076130414916, 'wp_1_0': -0.71090849677608803, 'wp_1_1': 0.934073482101346, 'wp_2_0': -0.00066187607410972968}, {}, {}, {'wm_1_2_0': -0.53808809742213326, 'wm_1_2_1': 5.5089353319456117e-07, 'wl_1': array([-0.37475327]), 'wl_2': array([ -1.04554824e-06]), 'wp_2_1': 0.19358359926657046, 'wp_1_0': -0.19860510166887396, 'wp_1_1': 1.0588286985302424, 'wp_2_0': -180.23580955504971}, {}, {'wm_1_2_0': -0.5075835010528531, 'wm_1_2_1': 4.0230554049750885e-07, 'wl_1': array([-0.38633144]), 'wl_2': array([ -1.07739536e-06]), 'wp_2_1': 0.26449489701310525, 'wp_1_0': -0.011501285892348041, 'wp_1_1': 1.3248057470110177, 'wp_2_0': -35.994070312905926}, {}, {}, {'wm_1_2_0': -0.089921433363637657, 'wm_1_2_1': -1.5519502241207109e-06, 'wl_1': array([-0.48531564]), 'wl_2': array([ -1.88420172e-06]), 'wp_2_1': 1.0008616366415897, 'wp_1_0': -3.404329014204615, 'wp_1_1': 0.82068365974726865, 'wp_2_0': -1.8466446833261077e-06}, {}, {'wm_1_2_0': -0.089921433363637657, 'wm_1_2_1': -1.5519502241207109e-06, 'wl_1': array([-0.48531564]), 'wl_2': array([ -1.88420172e-06]), 'wp_2_1': 1.0008616366415897, 'wp_1_0': -3.4043195863465612, 'wp_1_1': 0.82068391501108529, 'wp_2_0': -1.8466446833261077e-06}, {'wm_1_2_0': -0.37046176200936487, 'wm_1_2_1': -9.2732091943948523e-08, 'wl_1': array([-0.39648606]), 'wl_2': array([ -1.24313220e-06]), 'wp_2_1': 0.46881786282861754, 'wp_1_0': -0.0043841258466101136, 'wp_1_1': 1.4154883464066534, 'wp_2_0': -0.32961303253899904}, {'wm_1_2_0': -0.47330318226150347, 'wm_1_2_1': 3.0919545166931543e-07, 'wl_1': array([-0.38882434]), 'wl_2': array([ -1.20168307e-06]), 'wp_2_1': 0.34419080190077117, 'wp_1_0': -1.7505201500544101, 'wp_1_1': 0.85710786836950847, 'wp_2_0': -4.9707269805930627}, {'wm_1_2_0': 0.00098904420297138678, 'wm_1_2_1': -1.4850573200339901e-06, 'wl_1': array([-0.47602341]), 'wl_2': array([ -1.48243606e-06]), 'wp_2_1': 1.5945040184283172, 'wp_1_0': -0.01354620967200521, 'wp_1_1': 1.3396113936340199, 'wp_2_0': -1.0556529735719962e-12}]

all_temp_class = [{'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 15, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 25, 't1': 15}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 35, 't1': 25}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 4, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 7, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 4, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': 7, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': 35}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}]


all_fo_class = [{'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 34005.0, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 36264.0, 'dwt1': 34005.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 43716.0, 'dwt1': 36264.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 63599.0, 'dwt1': 43716.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 95649.0, 'dwt1': 63599.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 146356.0, 'dwt1': 95649.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 0.8, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.8, 'sg2': 0.9, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 0.9, 'sg2': 1.0, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': 1.0, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': 146356.0, 'wf1': -33333, 't2': 22222, 't1': -22222}, {'sg1': -44444, 'sg2': 44444, 'wf2': 33333, 'dwt2': 11111111111111L, 'dwt1': -11111, 'wf1': -33333, 't2': 22222, 't1': -22222}]


i=1

all_fo_const = [{}, {'w2': 0.0019505220141344871, 'w1': 0.00015783876674881878, 'w0': -9.0356602623945469e-06}, {'w2': -0.00060518964465400174, 'w1': 0.00024757004367470655, 'w0': 3.7823308019281143e-05}, {'w2': -0.0021621088060084226, 'w1': 5.9683866889657624e-05, 'w0': 3.3492919775221404e-05}, {'w2': 0.00084860755693940478, 'w1': 0.0001465175176394789, 'w0': -1.0686012246829161e-07}, {}, {'w2': -0.26276203228464207, 'w1': 0.00086768884346780681, 'w0': -6.0709873204119847e-06}, {'w2': 0.010742138215886703, 'w1': 0.00010907480546992716, 'w0': 8.5653580060478282e-06}, {'w2': 0.0033280177536508678, 'w1': 8.600264279296467e-05, 'w0': -2.1907196994018027e-05}, {'w2': 0.0032395674197051986, 'w1': 0.00012807264826729915, 'w0': 7.8663743831698196e-06}, {'w2': 0.14767272413372481, 'w1': -0.00067649011607171135, 'w0': 1.7936626772999684e-05}, {'w2': 0.0031279900221278557, 'w1': 0.00013082274688251295, 'w0': 3.3909769730667087e-05}, {'w2': 0.015513528447552506, 'w1': 0.00014261107213309356, 'w0': 7.9676893528946221e-06}, {'w2': 0.03806909054319934, 'w1': 2.66203631392189e-05, 'w0': 1.622928852803967e-05}, {'w2': 0.0034199189949388129, 'w1': 0.00012369352102744953, 'w0': 2.3106113768815246e-05}, {'w2': 0.0091440356399992619, 'w1': 0.00017399113667862466, 'w0': 2.1639460945794598e-06}, {'w2': -0.0020274291587145544, 'w1': 0.00017792163096029293, 'w0': 1.1552990760774809e-05}, {'w2': 0.021487965046000479, 'w1': 9.5860648370525774e-05, 'w0': 1.3750804412053104e-05}, {'w2': 0.015789037047504527, 'w1': 0.00013571083677065546, 'w0': -6.0004108829664964e-06}, {'w2': 0.00080271507876024948, 'w1': 0.00014120116295016864, 'w0': 1.3238577193890359e-05}, {}, {'w2': 0.098822428568803938, 'w1': -1.6363743735914688e-05, 'w0': 2.513688009356787e-07}, {'w2': 0.033558283244499686, 'w1': 0.00010390201130857521, 'w0': 4.2936485519679006e-06}, {'w2': 0.042362907378686185, 'w1': 0.00014255867255876377, 'w0': -1.2570732569509393e-05}, {'w2': 0.031906295290202974, 'w1': 0.00010043828235886883, 'w0': 2.9101501243805452e-06}, {'w2': 0.054690467991411751, 'w1': 7.543508652405341e-05, 'w0': -1.7271373573474237e-06}, {'w2': 0.025991209028066529, 'w1': 0.00015493859171074599, 'w0': 1.2447460197134673e-05}, {'w2': 0.033857898819211245, 'w1': 0.00013260214943872371, 'w0': 7.6514730054203508e-06}, {'w2': 0.045737816859561561, 'w1': 6.9962447781371869e-05, 'w0': 4.0904605669544439e-06}, {'w2': 0.015747914652895448, 'w1': 0.00014005158260044641, 'w0': 1.0827867565378373e-05}, {}, {'w2': 0.010010169569797531, 'w1': 0.00019035993384791311, 'w0': 8.7001354356764725e-06}, {'w2': 0.01855204218674467, 'w1': 0.00011649910868152202, 'w0': 1.7073065682780135e-05}, {'w2': 0.10318841191854382, 'w1': -5.8698330510409906e-05, 'w0': 1.4634201563210039e-05}, {'w2': 0.014748585322880245, 'w1': 0.00012521010135760314, 'w0': 1.5703366826401606e-05}, {'w2': 0.0020787133839343559, 'w1': 0.00014792114608203546, 'w0': 1.396082228727834e-05}]



chpId =  1516
tanks_data= getFirstChp(chpId)
dhtId = tanks_data['dht_id']
voyage_details=vd.VoyageDetails(chpId, dhtId)
tanks_data['etd_discharge_port'] = voyage_details.grades[tanks_data['tanks'][0]['cargo_grade']-1]['etd_discharge_port']
current_date =  tanks_data['first_dht_date']
while(current_date < tanks_data['etd_discharge_port']):

	current_date = current_date+timedelta(1)
	print 'plan for next day is', current_date
	#print 'updated tanks data of previous day'
	#print tanks_data
	tanks_data = getDailyConstantTank(tanks_data)
	print 'tanks detail after includeing constant for that day', tanks_data
	# for grade_no in range(1, dht['total_grade']+1):
	# 	category = get_class_chpid_dhtid(chpId, dhtId, grade_no)
	
	tanks_data =  make_plan_per_day(tanks_data, chpId, tanks_data['dht_id'])	
	qry = "select dht_id from dht_head where chp_id ='"+str(chpId)+"' and dht_date = '"+str(current_date)+"'"
	cursor.execute(qry)	
	tanks_data['dht_id'] = cursor.fetchone()['dht_id']
	qry="select sw_temp, air_temp, wind_force from dht_head where chp_id = '"+str(chpId)+"' and dht_id = '"+str(tanks_data['dht_id'])+"'"
	cursor.execute (qry)
	sw_air_wf= cursor.fetchone()
	amb_temp =(float(sw_air_wf['sw_temp'])+float(sw_air_wf['air_temp']))/2
	tanks_data['amb_temp'] = amb_temp
	tanks_data['wind_force'] =float(sw_air_wf['wind_force'])
	tanks_data['air_temp'] =  float(sw_air_wf['air_temp'])
	tanks_data['sea_temp']  =  float(sw_air_wf['sw_temp'])