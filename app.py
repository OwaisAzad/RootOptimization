import json
import os
import subprocess
import boto3
import datetime
import time
import requests
import sys
import math
from math import sin, cos, sqrt, atan2, radians
from pandas.io.json import json_normalize
import tzlocal
import pandas as pd
from pytz import timezone


def cal_distance(lat1, lng1, lat2, lng2):
    R = 6373.0
    lat1 = radians(float(lat1))
    lon1 = radians(float(lng1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lng2))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return sqrt(2)*R * c


def cal_min_interval(c):
    eastern = timezone('US/Eastern')
    local_timezone = tzlocal.get_localzone()
    order_hour = datetime.datetime.fromtimestamp(c, local_timezone).hour
    if order_hour < 8:
        prev_date = (datetime.datetime.today() - datetime.timedelta(days=1)).date()
        benchmark = str(prev_date) + " 08:00:00"
        benchmark = datetime.datetime.strptime(benchmark, '%Y-%m-%d %H:%M:%S')
        diff = datetime.datetime.fromtimestamp(c, local_timezone)- eastern.localize(benchmark)        
        time_interval = int((diff.total_seconds()) // 60)
    else:
        curr_date = datetime.datetime.today().date()
        benchmark = str(curr_date) + " 08:00:00"
        benchmark = datetime.datetime.strptime(benchmark, '%Y-%m-%d %H:%M:%S')
        diff = datetime.datetime.fromtimestamp(c, local_timezone)- eastern.localize(benchmark)
        time_interval = int((diff.total_seconds()) // 60)
    return time_interval


def lambda_handler(event, context):

    #get order info and driver info
    orderinfo=event["body"]["order"]
    driverinfo=event["body"]["driver"]


    #change driver info from json to dataframe
    driverTable=json_normalize(driverinfo)


    #change order info from json to dataframe
    orderTable=json_normalize(orderinfo)
    regions=orderTable.city_id.unique()
        
    #create dat file for each region
    for i in regions:
        regions_driver = driverTable.loc[driverTable["city_id"] == i]    
        region_driver = regions_driver["driver_id"]
        region_driver_num = len(region_driver)
        #print(region_driver_num)
        
        #create pref in dat
        pref = "Pref={ "+"\n"
        driver_ids_orders= [[row['driver_id'], row['orders']] for index, row in regions_driver.iterrows()]
        for g in driver_ids_orders:
            driver_id= g[0]
            for j in g[1]:
                order_id= j['id']
                pref=pref+ "<" + str(order_id) + ' '+ str(driver_id) + " 1>," + "\n"  
        pref=pref+ "};"+"\n \n"  
        #print(pref)


        #create truck and demand in dat
        demand = "Demands={ "+"\n" + "<0 0 0 0 0 0 0>,"+"\n"
        driver_pos = [ ['0', '0']] + [[row['lat'], row['lng']] for index, row in regions_driver.iterrows()]  
        truck= "Trucks={ "+ "\n"
        k=0
        for j in region_driver:
            truck= truck + "<" + str(k) + ' ' + str(j) + ' ' + str(k+1) + " 0 500 0 1200>,"+ "\n"
            demand= demand+ "<" + str(k+1) + ' ' + str(j) + " 0 0 0 0 0>," +"\n"
            k=k+1
        truck=truck+ "};" +"\n \n"
        #print(truck)
        
            
        regions_order = orderTable.loc[orderTable["city_id"] == i]
        #print(regions_order.to_json(orient='index'))
        demands_new = [[row['id'], row['cookingtime_set']] for index, row in regions_order.iterrows()]
        customer_new = [[row['customer_id'], row['shop_id']] for index, row in regions_order.iterrows()]
        shop_pos_new = [[row['shop_lat'], row['shop_lng']] for index, row in regions_order.iterrows()] 
        cus_pos_new = [[row['customer_lat'], row['customer_lng']] for index, row in regions_order.iterrows()] 
        date_time = [cal_min_interval(c) for c in regions_order["created_at"] ]

        demands_new_num= len(demands_new)
        demand= demand + ''.join(["<" + str(region_driver_num+m+1) + ' ' + str(customer_new[m][1]) + ' ' + str(demands_new[m][0]) + ' '+  str(date_time[m]) + ' '+ str(date_time[m]+180) + ' '  + str(demands_new[m][1] // 60) + " 1>,"+ "\n" for m in range(demands_new_num)])   
        
        regions_driver = regions_driver["orders"]     
        demands_old= [[row['id'], row['cookingtime_set']] for a in regions_driver for index, row in pd.DataFrame(a).iterrows()]
        customer_old= [[row['customer_id'], row['shop_id']] for a in regions_driver for index, row in pd.DataFrame(a).iterrows()]
        shop_pos_old= [[row['shop_lat'], row['shop_lng']] for a in regions_driver for index, row in pd.DataFrame(a).iterrows()]
        cus_pos_old= [[row['customer_lat'], row['customer_lng']] for a in regions_driver for index, row in pd.DataFrame(a).iterrows()]
        time_old= [cal_min_interval(t["created_at"]) for k in regions_driver for t in k]
       
        demands_old_num= len(demands_old)
        demand= demand + ''.join(["<" + str(region_driver_num + demands_new_num + m+1) + ' ' + str(customer_old[m][1]) + ' ' + str(demands_old[m][0]) + ' '+  str(time_old[m]) + ' '+ str(time_old[m]+180) + ' '  +  str(demands_old[m][1]//60) + " 1>,"+ "\n" for m in range(demands_old_num)])
        demand= demand + ''.join(["<" + str(region_driver_num +demands_new_num +demands_old_num+n+1) + ' ' + str(customer_new[n][0]) + ' ' + str(demands_new[n][0]) +  ' '+  str(date_time[n]) + ' '+ str(date_time[n]+180) + ' ' +  " 0 0>,"+ "\n" for n in range(demands_new_num)])
        demand= demand + ''.join(["<" + str(region_driver_num + 2*demands_new_num+demands_old_num+n+1) + ' ' + str(customer_old[n][0]) + ' ' + str(demands_old[n][0]) +' '+  str(time_old[n]) + ' '+ str(time_old[n]+180) + ' ' +  " 0 0>,"+ "\n" for n in range(demands_old_num)])   
        demand=demand+ "};"+"\n \n"  
        #print(demand)

    
        #create dist in dat
        dist = "Dists={ "+"\n"   
        line_num= 1+region_driver_num +2*demands_new_num+2*demands_old_num
        shop_pos= shop_pos_new + shop_pos_old
        cus_pos= cus_pos_new + cus_pos_old
        region_driver_num=region_driver_num+1
        for m in range(line_num):
            for n in range(line_num):
                if n==0 or m==0:
                    dist= dist + "<" + str(m) + ' ' + str(n) + " 0>,"+ "\n"
                elif n<region_driver_num and m<region_driver_num:
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(driver_pos[m][0], driver_pos[m][1], driver_pos[n][0], driver_pos[n][1]))) +  ">,"+ "\n"
                elif m<region_driver_num and region_driver_num<=n<(region_driver_num+len(shop_pos)):   
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(driver_pos[m][0], driver_pos[m][1], shop_pos[n-region_driver_num][0], shop_pos[n-region_driver_num][1]))) + ">," + "\n"  
                elif m<region_driver_num and (region_driver_num+len(shop_pos))<=n<line_num:   
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(driver_pos[m][0], driver_pos[m][1], cus_pos[n-region_driver_num-len(shop_pos)][0], cus_pos[n-region_driver_num-len(shop_pos)][1]))) + ">," + "\n" 
                elif n<region_driver_num and region_driver_num<=m<(region_driver_num+len(shop_pos)):   
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(shop_pos[m-region_driver_num][0], shop_pos[m-region_driver_num][1], driver_pos[n][0], driver_pos[n][1]))) + ">," + "\n"  
                elif n<region_driver_num and (region_driver_num+len(shop_pos))<=m<line_num:   
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(cus_pos[m-region_driver_num-len(shop_pos)][0], cus_pos[m-region_driver_num-len(shop_pos)][1], driver_pos[n][0], driver_pos[n][1]))) + ">," + "\n"  
                elif region_driver_num<=n<(region_driver_num+len(shop_pos)) and region_driver_num<=m<(region_driver_num+len(shop_pos)):                
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(shop_pos[m-region_driver_num][0], shop_pos[m-region_driver_num][1], shop_pos[n-region_driver_num][0], shop_pos[n-region_driver_num][1]))) + ">," + "\n"  
                elif (region_driver_num+len(shop_pos))<= n <=line_num and region_driver_num <=m<(region_driver_num+len(shop_pos)):
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(shop_pos[m-region_driver_num][0], shop_pos[m-region_driver_num][1], cus_pos[n-region_driver_num-len(shop_pos)][0], cus_pos[n-region_driver_num-len(shop_pos)][1]))) + ">," + "\n"  
                elif (region_driver_num+len(shop_pos))<= m <=line_num and region_driver_num <= n<(region_driver_num+len(shop_pos)):            
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(cus_pos[m-region_driver_num-len(cus_pos)][0], cus_pos[m-region_driver_num-len(cus_pos)][1], shop_pos[n-region_driver_num][0], shop_pos[n-region_driver_num][1]))) + ">," + "\n"  
                else: 
                    dist= dist + "<" + str(m) + ' ' + str(n) + ' ' + str(3*math.ceil(cal_distance(cus_pos[m-region_driver_num-len(cus_pos)][0], cus_pos[m-region_driver_num-len(cus_pos)][1], cus_pos[n-region_driver_num-len(cus_pos)][0], cus_pos[n-region_driver_num-len(cus_pos)][1]))) + ">," + "\n"  
        dist=dist+ "};"+"\n \n"
        #print(dist)


        dat = demand+ dist+ truck+ "Obj={ \n<0 travel_time 1 1>, \n<1 load_balance 1 500>, \n};"+"\n" +pref
        with open('/tmp/datafile.dat', 'w') as f:
            f.write(dat)


        #throw dat to opl 5 times to get a driver list
        #start_rwfile_time = datetime.datetime.now()
        path = os.environ['LAMBDA_TASK_ROOT']
        driverList=[]
        for i in range (5):
            proc = subprocess.Popen([path+'/oplrun','Root_Optimization.mod', '/tmp/datafile.dat'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()   
            data = out.decode('utf-8')

            #clean extra info in return
            check = data.find('**')
            if (check == -1):
                message="We don't have optimal solution for this case"
                driverList.append(message)
                #return {"body" : json.dumps(message)}
            else:
                message=[]
                array=[]
                pair=[]
                pairs={}
                position_end = data.find('<<< post process')   
                data = data[check:position_end].splitlines()
                for i in data:
                    array=array + i.split('**')
                array = list(filter(None, array))
                for i in range(len(array) // 2):
                    message.append(json.dumps({"order_id" : array[2*i], "deliverer_id" : array[2*i+1]})) 
                    pair.append({"order_id" : array[2*i], "deliverer_id" : array[2*i+1]})
                pairs=pair            
                driverList.append(message)
                #print(*message, sep='\n')
                #end_rwfile_time = datetime.datetime.now()
 
          
            #add additional pref to produce driver list
            new_order_id= demands_new[0][0]
            for m in pairs:
                if new_order_id  == int (m["order_id"]):
                    pre_driver_id= int(m["deliverer_id"])
                dat.insert(len(dat) - 2, "<"+ str(new_order_id) +' '+ str(pre_driver_id) + " 0>,"+"\n")
            with open('/tmp/datafile.dat', 'w+') as f:
                for i in range(len(dat)):
                    f.write(dat[i])  

        print(json.dumps(driverList))
        return {"body" : json.dumps(driverList)}
             #"body" :  + '\n time: ' + str(int((end_rwfile_time - start_rwfile_time).total_seconds() * 1000))
            
  


