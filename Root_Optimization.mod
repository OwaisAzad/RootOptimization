/*********************************************
 * OPL 12.8.0.0 Model
 *********************************************/
include "preprocessing_functions.mod";

using CP;

string python_path = "/var/lang/bin/python3";

// date and region parameters from controller.
int region = ...;
string date_start = ...;
string date_end = ...;
 
// Data structure for a CP model given date and region 


tuple UnindexedPosition {
   int id;
   int order_id;  // OPL only reads in non-identical entries, so we use order_id to distinguish restaurants with multiple orders
   int position_id;
   float x;
   float y;
};

tuple Position {
   key int id;
   int position_id;
   float x;
   float y;
};
 
tuple UnindexedDemand {
   int id;
   int position_id;
   int order_id;
   int min_time;
   int max_time;
   int est_time;
   int quantity;
};

tuple Demand {
   key int id;
   int position_id;
   int order_id;
   int min_time;
   int max_time;
   int est_time;  // drop-off time at the customers is set to 3 minutes
   int quantity;
};

tuple Vehicle {
	key int vehicleID;	
	int driver_id;
	int first_visit_id;
	int last_visit_id;
	int	capacity;
	int start_time;
	int end_time;
};	

{UnindexedPosition} UnindexedDrivers = ...;
{UnindexedPosition} UnindexedPositions = ...;
{UnindexedDemand} UnindexedDemands = ...;

execute preprocessing_1{ // Add unique index to the tuples
	ComputeIndex(UnindexedDemands,SetIndex, 2);
	ComputeIndex(UnindexedPositions,SetIndex, 2);
	ComputeIndex(UnindexedDrivers,SetIndex, 0);
}
{Demand} Demands = {<u.id, u.position_id, u.order_id, u.min_time, u.max_time, u.est_time, u.quantity> | u in UnindexedDemands};
{Position} Positions = {<u.id, u.position_id, u.x, u.y> | u in UnindexedPositions};
{Position} Drivers = {<u.id, u.position_id, u.x, u.y> | u in UnindexedDrivers};

int horizon = 1200;  // Time starts from 8am (0 min) to 4am (1200 min)
int truck_capacity = 500;  // Set to a large value to allow flexibility
{Vehicle} Trucks = {<d.id, d.position_id, 0, 0, truck_capacity, 0, horizon> | d in Drivers};				    
//int numTrucks = card(Trucks);

tuple Dist { int c1; int c2; int d; }; // d is distance in meters
{Dist} Dists = {<p1.id,p2.id, -1> | p1, p2 in Positions };

execute preprocessing_2 {  
	ComputeTripTime(Dists,Positions,ComputePairTime); // Compute the travelling times between each pair of locations
};


execute {  // Check if all input data are correct
	writeln("region: ", region, " date_start: ", date_start, " date_end: ", date_end);
	//writeln("Distance computed")
	//writeln(Dists);
	writeln("Trucks");
	writeln(Trucks);
	writeln("Demands");
	writeln(Demands);
};


assert forall(d in Dists) d.d >= 0;  // Make sure all distances are computed
assert card(Positions) == card(Demands); // Positions and Demands should have identical entries

dvar interval visit [d in Demands] in d.min_time..d.max_time size d.est_time;
dvar interval tvisit[d in Demands][t in Trucks] optional(d.id>1) size d.est_time;
dvar sequence route[t in Trucks] in all(d in Demands) tvisit[d][t] types all(d in Demands) d.id;
//dvar interval truck [t in Trucks] optional;
 
// Objective functions:
dexpr float travelTime = sum(t in Trucks) endOf(tvisit[<1>][t]);
//dexpr int nbUsed = sum(t in Trucks) presenceOf(truck[t]);  // TODO: Currently, every truck is not optional, so this doens't work
dexpr int load[t in Trucks] = sum(d in Demands) presenceOf(tvisit[d][t]) * d.quantity;
dexpr int loadBalancer = max(t in Trucks) load[t] - min(t in Trucks) load[t];
//dexpr int makespan = max(a in allActivities) endOf(activity[a]);// Complete makespan expression;

execute set_params {
   cp.param.TimeMode = "ElapsedTime";
   cp.param.TimeLimit = 2;
   cp.param.Workers = 1;
   cp.param.logPeriod = 1000000;
   // On this type of problem, search phase on sequence variable may help
   // var f = cp.factory;
   // cp.setSearchPhases(f.searchPhase(route));
};

minimize staticLex(loadBalancer,travelTime); 
// minimize travelTime;
//minimize travelTime + 500*loadBalancer; 
 constraints {
   forall(t in Trucks) {
     noOverlap(route[t], Dists);     // Travel time
     first(route[t],tvisit[<0>][t]); // Truck t starts at depot
     last (route[t],tvisit[<1>][t]); // Truck t ends at depot
     sum(d in Demands) presenceOf(tvisit[d][t])*d.quantity <= truck_capacity; // Truck capacity
     //     before(route[t],tvisit[<166631>][t],tvisit[<813706>][t]);
   }
   
   // Given an order, the restaurant should be visited before the customer
   forall(t in Trucks) {
   	forall(d1 in Demands, d2 in Demands: d1.id > 1 && d2.id > 1 && d1.order_id == d2.order_id && d1.position_id < d2.position_id){
   	   	before(route[t],tvisit[d1][t],tvisit[d2][t]);
   	   	presenceOf(tvisit[d1][t]) == presenceOf(tvisit[d2][t]);
   	}   
   }

   forall(d in Demands: d.id>1) {
     alternative(visit[d], all(t in Trucks) tvisit[d][t]); // Truck selection
   }
//   loadBalancer <= 1;
}

