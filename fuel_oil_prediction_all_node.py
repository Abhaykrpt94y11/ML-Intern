import MySQLdb
import json
from dateutil import parser
import collections
import time
import datetime
import math
from datetime import date, timedelta
from datetime import datetime as dt
from numpy import arange,array,ones,linalg
import numpy as np
from pylab import plot,show

conn = MySQLdb.connect (host = "localhost",user = "root", passwd = "", db = "heatsolc")
cursor = conn.cursor (MySQLdb.cursors.DictCursor)


def find_constants(true_data_set_all, y_value_all):

	a = []
	b = []
	c = []

	for i in range (0, len(true_data_set_all)):
		a.append(true_data_set_all[i]['x1'])
		b.append(true_data_set_all[i]['x2'])
		c.append(true_data_set_all[i]['x3'])

		A1 =  [a,b,c]
		x1 = np.array(a)
		x2 = np.array(b)
		x3 = np.array(c)
		A = array([a,b,c])

	# linearly generated sequence
	#print 'Ais', A
	y = y_value_all


	#print 'yis', y
	#print 'Att', A.T
	l =  len(a)

	w = linalg.lstsq(A.T,y)[0] # obtaining the parameters
	#print 'wis', w
	# plotting the line

	print
	print
	print 'parameters for regression lines is'
	print'w0' ,w[0]
	print 'w1', w[1]
	print 'w2', w[2]
	line = w[0]*a+w[1]*b+w[2]*c # regression line

	 #plot(A,line,'r-',A,y,'o')
	 #plot(A1, line,'r-', A1, y,'o')

	 #show()
	return w

def get_data_class(dwt1, dwt2, t1, t2, wf1, wf2, s1, s2):

	qry ="select dh.chp_id, dh.air_temp, dh.sw_temp, hm.avg_observed_cargo_temp, ct.api_sp_gravity, dh.bc_cargo_heating, dh.dht_id, dh.dht_date, ct.grade_no from hla_main hm,  dht_head dh, "+\
	" chp_head ch , chp_trans ct, dimensionmaster dm  where hm.chp_id = dh.chp_id and dh.chp_id = ch.chp_id and "+\
	" ch.chp_id = ct.chp_id and hm.dht_id =  dh.dht_id  and dm.vess_id = ch.vess_id and hm.grade_no =  ct.grade_no and  "+\
	" dh.bc_cargo_heating >0 and (dm.DWT >= '"+str(dwt1)+"' and dm.DWT<'"+str(dwt2)+"') and (dh.wind_force >='"+str(wf1)+"' and dh.wind_force < '"+str(wf2)+"') "+\
	"  and (((dh.temp_type ='C' and dh.sw_temp<>0 and dh.air_temp<>0 ) and hm.avg_observed_cargo_temp<>0) and ((hm.avg_observed_cargo_temp-(dh.sw_temp+dh.air_temp)/2)>= '"+str(t1)+"' "+\
	" and (hm.avg_observed_cargo_temp-(dh.sw_temp+dh.air_temp)/2)<'"+str(t2)+"')) and "+\
	" ((ct.api_sp_gravity> 1.2 and (141.5/(131.5 + ct.api_sp_gravity)>='"+str(s1)+"' and 141.5/(131.5 + ct.api_sp_gravity)<'"+str(s2)+"')) "+\
	" OR (ct.api_sp_gravity<0.7 and (141.5/(131.5 + ct.api_sp_gravity)>='"+str(s1)+"' and 141.5/(131.5 + ct.api_sp_gravity)<'"+str(s2)+"')) "+\
	" OR ((ct.api_sp_gravity>=0.7 and ct.api_sp_gravity<=1.2) and ct.api_sp_gravity>='"+str(s1)+"' and ct.api_sp_gravity <'"+str(s2)+"')) order by dh.dht_date, dh.chp_id"

	cursor.execute(qry)
	rows =  cursor.fetchall()
	all_data  = {}
	for row in rows:

		chp_id= row['chp_id']
		dht_id = row['dht_id']
		if chp_id not in all_data.keys():
			all_data[chp_id] = {}
		if dht_id not in all_data[chp_id].keys():
			all_data[chp_id][dht_id] =[]
		try:
			if(float(row['api_sp_gravity']) >1.2 or float(row['api_sp_gravity'])<0.7):
				row['api_sp_gravity'] = 141.5/(131.5+float(row['api_sp_gravity']))
		except:
			row['api_sp_gravity'] =  0.9
			pass

		amb =  (row['sw_temp']+row['air_temp'])/2
		all_data[chp_id][dht_id].append({'dht_id':row['dht_id'] , 'chp_id':row['chp_id'], 'api_sp_gravity': row['api_sp_gravity'], \
		'bc_cargo_heating':row['bc_cargo_heating'],'dht_date':row['dht_date'],\
		'avg_observed_cargo_temp':float(row['avg_observed_cargo_temp']),'grade_no':row['grade_no'],\
		'amb_temp':amb})
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

def find_futures(all_data):

	x_1 = []
	x_2 = []
	x_3= []
	y_1_2_3 =  []

	for key in all_data.keys():
		for ky in all_data[int(key)].keys():
			
			heat_raise = 0
			#key = 1599
			x1=0
			x2 = 0
			x3 = 0
			y=0
			flag = 0

			for i in range(0, len(all_data[int(key)][int(ky)])):
				#print '1599 dksdlsa', all_data[key][ky][i]['dht_id']
				##print 'chpid and dht_id is', key, ' ', ky , 'and date is', all_data[key][ky][i]['dht_date']
				q1 = "select sum(dt.qty), hm.avg_observed_cargo_temp from dht_trans dt, hla_main hm where dt.dht_id= '"+str(ky)+"' and dt.chp_id='"+str(key)+"' "+\
				"and dt.cargo_grade ='"+str(all_data[key][ky][i]['grade_no'])+"' and dt.chp_id = hm.chp_id and "+\
				"dt.dht_id = hm.dht_id and dt.cargo_grade = hm.grade_no "

				cursor.execute(q1)
				r1 =cursor.fetchone()
				#print 'r1111',r1
				q2 = "select sum(dt.qty), hm.hla_date, hm.avg_observed_cargo_temp from dht_trans dt, hla_main hm where dt.chp_id='"+str(key)+"' "+\
				"and dt.cargo_grade ='"+str(all_data[key][ky][i]['grade_no'])+"' and dt.chp_id = hm.chp_id and "+\
				"dt.dht_id = hm.dht_id and dt.cargo_grade = hm.grade_no and hm.hla_date = '"+ str(all_data[key][ky][i]['dht_date']+timedelta(1))+"' "
				cursor.execute(q2)
				r2 =cursor.fetchone()

				#q2 = "select sum(qty) from dht_trans where dht_id= '"+str(ky)+"' and chp_id='"+str(key)+"' "+\
				#"and cargo_grade ='"+str(all_data[key][ky][i]['grade_no'])+"' and hm.hla_date = '"+ str(all_data[key][ky][i]['dht_date']+timedelta(1))+"'"		
				d1 = "select temp_type from dht_head where chp_id='"+str(key)+"' and dht_id='"+str(ky)+"'"
				cursor.execute(d1)
				try:
					a =cursor.fetchone()
					##print a
					##print 'len a', len(a)
					d2 = "select dht_id from dht_head where chp_id ='"+str(key)+"' and dht_date='"+ str(all_data[key][ky][i]['dht_date']+timedelta(1))+"'"
					cursor.execute(d2)
					b =cursor.fetchone()

					d3 = "select temp_type from dht_head where chp_id='"+str(key)+"' and dht_id='"+str(b['dht_id'])+"'"
					cursor.execute(d3)
					c =cursor.fetchone()

					#if(a and b and c):
					if(a['temp_type']=='C' and c['temp_type']=='C' and r2['avg_observed_cargo_temp']!=None and r2['sum(dt.qty)']!=None and (r1['sum(dt.qty)']==r2['sum(dt.qty)'])):

						#print 'alldddddd' , all_data[key][ky][i]
						print 'current date detail', 'qty1', r1['sum(dt.qty)'] , 'avgtmp1', r1['avg_observed_cargo_temp']
						print 'next day detail', 'qty2', r2['sum(dt.qty)'] , 'avgtmp2', r2['avg_observed_cargo_temp'], 'hla_data is', r2['hla_date']
						heat_raise+=1
						avg_avg_obs= (float(r1['avg_observed_cargo_temp'])+float(r2['avg_observed_cargo_temp']))/2
						q3 =  "select sw_temp , air_temp from dht_head where dht_date = '"+ str(all_data[key][ky][i]['dht_date']+timedelta(1))+"' "+\
						"and  chp_id = '"+str(key)+"' "
						cursor.execute(q3)
						r3 =cursor.fetchone()


						if(float(r2['avg_observed_cargo_temp'])-float(r1['avg_observed_cargo_temp']) >0):
							avg_amb = ((float(r3['sw_temp'])+float(r3['air_temp']))/2+ float(all_data[key][ky][i]['amb_temp']))/2

							sh = ((float(all_data[key][ky][i]['avg_observed_cargo_temp']) + 32) * 1.8 + 671) * (2.1- float(all_data[key][ky][i]['api_sp_gravity']))/2030 * 1/0.2388
							x1+=(float(r1['sum(dt.qty)'])*float(sh)*(float(r2['avg_observed_cargo_temp'])-float(r1['avg_observed_cargo_temp'])))
							x2+=(math.pow(float(r1['sum(dt.qty)']), 2.0/3)*(float(avg_avg_obs)-float(avg_amb)))
							x3+=(100-float(avg_amb))
							print 'data for grade detail is', all_data[key][ky][i]
							print 'x1 , x2, x3,y for this grade is', x1, ' ', x2, ' ', x3, ' ', y
							flag =1
				except:
					pass

			if(flag):
				print 'summing over alll grade x1,x2,x3,'
				print 'x1, x2, x3, y', x1, ' ', x2,' ', x3,' ', y
				x_1.append(x1)
				x_2.append(x2)
				x_3.append(x3)
				y_1_2_3.append(float(all_data[key][ky][0]['bc_cargo_heating']))


	return x_1,x_2,x_3,y_1_2_3


def find_constants(a, b,c,y):

	A1 =  [a,b,c]
	x1 = np.array(a)
	x2 = np.array(b)
	x3 = np.array(c)
	A = array([a,b,c])
	l =  len(a)

	w = linalg.lstsq(A.T,y)[0] 

	print
	print
	print 'parameters for regression lines is'
	print'w0' ,w[0]
	print 'w1', w[1]
	print 'w2', w[2]
	line = w[0]*a+w[1]*b+w[2]*c  
	return w

DWT= [-11111, 34005.00,36264.00,43716.00, 63599.00 , 95649.00,146356.00, 11111111111111]
SG = [-44444, 0.80, 0.90, 1.0, 44444]

all_level_class =[]
all_x1 =[]
all_x2 = []
all_y = []
all_class_nodes = []
all_class_nodes_const = []

def get_all_node_classs_data():

 # cl = 0

 	xx1 =[]
 	xx2 = []
 	xx3 = []
 	yy = []
 	for i in range(0, len(DWT)-1):

		for l in range(0, len(SG)-1): 

			d= {'dwt1':DWT[i], 'dwt2': DWT[i+1], 't1':-22222, 't2':22222, 'wf1': -33333, 'wf2':33333, 'sg1':SG[l], 'sg2':SG[l+1]}
  			all_data = get_data_class(DWT[i],DWT[i+1],-22222,22222, -33333, 33333, SG[l], SG[l+1])
  			
   			
   			x1,x2,x3,y= find_futures(all_data)
   			print 'x1 x2 x3 y is'
   			print len(x1), ' ', len(y)
   			if(len(x1)):
   				c = find_constants(x1,x2,x3,y)
   				const ={'w0':c[0], 'w1':c[1], 'w2':c[2]}
   				print 'costant array  is', c

   			else:
   				const = {}

			all_class_nodes.append(d)
			all_class_nodes_const.append(const)

		
			print 'length of all equal vectors are  ', len(x1) , ' ', len(x2), ' ', len(x3) , len(y)
			print 'current class and constant is'
			print d
			print const

			print 'current all nodes till ', len(all_class_nodes)
			print 'current all nodes constant are for leaves nodes are', len(all_class_nodes_const)

			xx1.append(x1)
			xx2.append(x2)
			xx3.append(x3)
			yy.append(y)

		print 'calculating constant for internal nodes'
		d= {'dwt1':DWT[i], 'dwt2': DWT[i+1], 't1':-22222, 't2':22222, 'wf1': -33333, 'wf2':33333, 'sg1':SG[0], 'sg2':SG[len(SG)-1]}
	  	all_data = get_data_class(DWT[i],DWT[i+1],-22222,22222, -33333, 33333, SG[0], SG[len(SG)-1])
	  	x1,x2,x3,y= find_futures(all_data)
		print len(x1), ' ', len(y)
		#c= []
		if(len(x1)):
			c = find_constants(x1,x2,x3,y)
			const ={'w0':c[0], 'w1':c[1], 'w2':c[2]}
			print 'costant array  is', c

		else:
			const = {}
		all_class_nodes.append(d)
		all_class_nodes_const.append(const)
		xx1.append(x1)
		xx2.append(x2)
		xx3.append(x3)
		yy.append(y)

		print 'length of all equal vectors are  ', len(x1) , ' ', len(x2), ' ', len(x3) , len(y)
		print 'current class and constant is for intern nodes is'
		print d
		print const


	print 'calculating constant for root nodes'
	d= {'dwt1':DWT[0], 'dwt2': DWT[len(DWT)-1], 't1':-22222, 't2':22222, 'wf1': -33333, 'wf2':33333, 'sg1':SG[0], 'sg2':SG[len(SG)-1]}
  	all_data = get_data_class(DWT[0],DWT[len(DWT)-1],-22222,22222, -33333, 33333, SG[0], SG[len(SG)-1])
  	x1,x2,x3,y= find_futures(all_data)
	print len(x1), ' ', len(y)
	#c= []
	if(len(x1)):
		c = find_constants(x1,x2,x3,y)
		const ={'w0':c[0], 'w1':c[1], 'w2':c[2]}
		print 'costant array  is', c

	else:
		const = {}

	all_class_nodes.append(d)
	all_class_nodes_const.append(const)
	xx1.append(x1)
	xx2.append(x2)
	xx3.append(x3)
	yy.append(y)

	print 'length of all equal vectors are  ', len(x1) , ' ', len(x2), ' ', len(x3) , len(y)
	print 'current class and constant for root is'
	print d
	print const

	return all_class_nodes, all_class_nodes_const, xx1, xx2, xx3, yy	

##############Functioin calling start #############################################


all_const, all_class, all_x1 , all_x2, all_x3, all_y = get_all_node_classs_data()


print 'FINAL DATA ARRAY AND CONSTANTS ARE'
print
print len(all_x1) , all_x1
print len(all_x2), all_x2
print len(all_x3), all_x3	
print len(all_y), all_y

print 'FINAL NODES AND CONSTANT ARRAY ARE'
print len(all_class)
print 
print all_class

print
print len(all_const)
print
print all_const


# dwt1=  -9239839
# dwt2 = 82039183021
# t1 = -213323
# t2 =  1823218390
# wf1 = -21123
# wf2 = 12390293
# s1= -293182
# s2 = 832839023



#all_data =  get_data_class(dwt1, dwt2, t1, t2, wf1, wf2, s1,s2)

# x1,x2,x3,y = find_futures(all_data)
# print 'all futures is x1', len(x1) , 'len y', len(y)
# print 'x1', len(x1) , x1
# print 'x2' , len(x2) , x2
# print 'x3' , len(x3) , x3
# print 'y' , len(y) , y


# w = find_constants(x1,x2,x3,y)
# print 'constants for all data from entire database ', w


# print 'data for chpId 1599 ', len(all_data[1599])
# print all_data[1599]