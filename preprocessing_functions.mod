execute
{
	function ComputeTripTime(dist,Positions,ComputePairTime){
		for(var i=0;i<=dist.size-1;i++){
	    	var it=Opl.item(dist,i);
	    	ComputePairTime(it,Positions);
		}
	}
	
	function ComputePairTime(it,Positions){		
		var lat1 = Positions.find(it.c1).x;
		var lat2 = Positions.find(it.c2).x;
		var lon1 = Positions.find(it.c1).y;
		var lon2 = Positions.find(it.c2).y;	
		var p = 0.017453292519943295;     
		var a = 0.5 - Math.cos((lat2 - lat1) * p)/2 + Math.cos(lat1 * p) * Math.cos(lat2 * p) * (1 - Math.cos((lon2 - lon1) * p)) / 2;
		// i.d is the estimated distance in meters
		var d = 12742 * Math.asin(Math.sqrt(a)) * 1000
		var adj_d = (d/Math.sqrt(2))*2;
		var time_mins = Math.round(     adj_d / 16.6667 / 20    ); // Assuming a 20km/hr speed
		it.d = time_mins;
	}
	
	function ComputeIndex(Demands, SetIndex, init_index){
		for(var i=init_index;i<=Demands.size-1;i++){
	    	var it=Opl.item(Demands,i);
	    	SetIndex(it,i,Demands);
		}
	}
	
	function SetIndex(it,i,Demands){
		it.id = i;
	}
    

} // The end of the execute block
