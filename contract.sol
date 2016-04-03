contract mortal {
	address alarm = 0xb8da699d7fb01289d4ef718a55c3174971092bef;
	
    /* Define variable owner of the type address*/
    address public owner;

    /* this function is executed at initialization and sets the owner of the contract */
    function mortal() { owner = msg.sender; }

    /* Function to recover the funds on the contract */
    function kill() onlyOwner { if (msg.sender == owner) suicide(owner); }
	
	//Restrict action to owner
	modifier onlyOwner {
		if (msg.sender != owner) throw;
		_
	}
	
	function alarmIt(bytes4 sig, uint futureBlock){
		// the 4-byte signature of the scheduleCall function.
        bytes4 scheduleCallSig = bytes4(sha3("scheduleCall(bytes4,uint256)"));

        alarm.call(scheduleCallSig, sig, futureBlock);
	}
	
	function max(uint a, uint b) returns (uint) {
    	if (a > b) return a;
    	else return b;
  	}
}

contract abstractAuction is mortal {
	address public seller;
	address public buyer;
	uint public price;
	uint public ID;
}

contract auctionWithLocation is abstractAuction {
	
	
	bytes32 loc;
	bytes32 shipping;
	
	function getShipInfo() onlyOwner returns (bytes32, bytes32) {
		return (loc,shipping);
	}
}

contract auction is abstractAuction {
	uint public endTime;
	bytes4 public sig;
	
    // This is the constructor which registers the
    // creator and the assigned name.
    function auction(address sellerAd, uint minBid, uint lengthInHours, uint _ID){
		price = minBid;
		buyer = 0;
		seller = sellerAd;
		
		ID = _ID;
		
		// the 4-byte signature of the local function we want to be called.
        sig = bytes4(sha3("concludeAuction()"));
		
		//targetBlock
		uint futureBlock = block.number + max(10,(lengthInHours * (60*4)));
		
		//end time
		endTime = now + (lengthInHours * (1 hours));
		
		//Alarm calls
		alarmIt(sig,futureBlock);
    }
	
	function concludeAuction() {
		if(now < endTime){
			uint futureBlock = block.number + max(10,(endTime - now)/(60/4));
			alarmIt(sig,futureBlock);
		}else{
			auctionEscrow casted = auctionEscrow(owner);
			casted.auctionEnded(price,buyer,seller,ID);
			this.kill();
		}
	}
	
	function() {
		if(now > endTime){
			throw;
		}
		uint bid = msg.value;
		if(bid <= price){
			throw;
		}
		
		if(buyer != 0){
			buyer.send(price);
		}
		
		buyer = msg.sender;
		price = bid;
	}
}

contract shippingManager is auctionWithLocation {
	
	
	//State is the state of this contract
	//0: Initial state, no information
	//1: Address added
	//2: Shipping number added
	uint state;
	
	function shippingManager(uint _price, address _buyer, address _seller, uint _ID){
		state = 0;
		price = _price;
		buyer = _buyer;
		seller = _seller;
		ID = _ID;
		
		loc = "";
		shipping = "";
		
		//4 days waiting
		uint targetBlock = block.number + (60/4)*60*24*4;
		
		bytes4 sig = bytes4(sha3("killIfNoAddress()"));
		
		alarmIt(sig,targetBlock);
	}
	
	function addShippingAddress(bytes32 _loc){
		if(state != 0){
			throw;
		}
		
		if(msg.sender != buyer){
			throw;
		}
		
		loc = _loc;
		state = 1;
		
		//4 days waiting
		uint targetBlock = block.number + (60/4)*60*24*4;
		
		bytes4 sig = bytes4(sha3("killIfNoShippingNumber()"));
		
		alarmIt(sig,targetBlock);
	}
	
	function killIfNoAddress(){
		if(state < 1){
			auctionEscrow casted = auctionEscrow(owner);
			casted.shippingFailed(ID,price,buyer);
			this.kill();
		}
	}
	
	function addShippingNumber(bytes32 num){
		if(state != 0){
			throw;
		}
		
		if(msg.sender != seller){
			throw;
		}
		
		shipping = num;
		state = 2;
		
		auctionEscrow casted = auctionEscrow(owner);
		casted.shippingInitiated(price,buyer,seller,ID,loc,shipping);
	}
	
	function killIfNoShippingNumber(){
		if(state < 2){
			auctionEscrow casted = auctionEscrow(owner);
			casted.shippingFailed(ID,price,buyer);
		}
		//kill it regardless, it has now recieved the funds back from the stopwatch
		this.kill();
	}
	
}

contract hairTrigger is auctionWithLocation {
	uint finished;
	
	uint started;
	
	function hairTrigger(uint _price, address _buyer, address _seller, uint _ID, bytes32 _loc, bytes32 _shipping){
		price = _price;
		buyer = _buyer;
		seller = _seller;
		ID = _ID;
		loc = _loc;
		shipping = _shipping;
		
		finished = 0;
		started = now;
		
		//21 days waiting, then assumes success
		uint targetBlock = block.number + (60/4)*60*24*21;
		
		bytes4 sig = bytes4(sha3("timeout()"));
		
		alarmIt(sig,targetBlock);
	}
	
	function recieved() {
		//recieved, no issues reported
		auctionEscrow casted = auctionEscrow(owner);
		casted.shippingSuccess(price,buyer,seller,ID,loc,shipping);
		finished = 1;
	}
	
	function timeout(){
		if(finished == 0){
			this.recieved();
		}
		//only kill after callback occurs
		this.kill();
	}
	
	function buyerRecieved(){
		if (msg.sender == buyer){
			this.recieved();
		}else{
			throw;
		}
	}
	
	function buyerProblem(){
		if (msg.sender == buyer){
			//issues with reception
			uint timegap = now - started;
			auctionEscrow casted = auctionEscrow(owner);
			casted.shippingFailure(price,buyer,seller,ID,loc,shipping,timegap);
			finished = 1;	
		}else{
			throw;
		}
	}
}

contract finishedAuction is abstractAuction {	
	function finishedAuction(uint _price, address _buyer, address _seller, uint _ID){
		price = _price;
		buyer = _buyer;
		seller = _seller;
		ID = _ID;
	}
}

contract disputeResolution is auctionWithLocation {	
	uint resolutionPrice;
	bool buyerSubmitted;
	bytes buyerMessage;
	bool sellerSubmitted;
	bytes sellerMessage;
	
	//false means cancel auction, true means delivered
	
	function disputeResolution(uint _price, address _buyer, address _seller, uint _ID, bytes32 _loc, bytes32 _shipping, uint resolutionPrice){
		price = _price;
		buyer = _buyer;
		seller = _seller;
		ID = _ID;
		loc = _loc;
		shipping = _shipping;
		
		//21 days waiting, then assumes success
		uint targetBlock = block.number + (60/4)*60*24*21;
		
		bytes4 sig = bytes4(sha3("timeout()"));
		
		alarmIt(sig,targetBlock);
		
		buyerSubmitted = false;
		sellerSubmitted = false;
	}
	
	function(){
		if(msg.value < resolutionPrice){
			throw;
		}
		uint diff = msg.value - resolutionPrice;
		if(msg.sender == buyer){
			if(buyerSubmitted){throw;}
			buyerSubmitted = true;
			buyerMessage = msg.data;
			buyer.send(diff);
		}else if(msg.sender == seller){
			if(sellerSubmitted){throw;}
			sellerSubmitted = true;
			sellerMessage = msg.data;
			seller.send(diff);
		}else{
			throw;
		}
	}
	
	//If neither responded: assumed to be delivered
	//If one responded: assumed they were truthful
	//If both responded: block on arbitration
	function timeout(){
		auctionEscrow casted = auctionEscrow(owner);
		if(!buyerSubmitted && !sellerSubmitted){
			casted.shippingSuccess(price,buyer,seller,ID,loc,shipping);
			kill();
		}else if(!buyerSubmitted && sellerSubmitted){
			casted.shippingSuccess(price,buyer,seller,ID,loc,shipping);
			kill();
		}else if(buyerSubmitted && !sellerSubmitted){
			casted.shippingFailed(ID,price,buyer);
			kill();
		}else{
			Arbitrate(this,ID,price,shipping,buyerMessage,sellerMessage);
		}
	}
	
		
	event Arbitrate(
        address indexed _from,
		uint indexed ID,
		uint price,
		bytes32 shipping,
		bytes buyerData,
		bytes sellerData
    );
	
	//positive result indicates decision for seller (shipping success)
	//negative result indicates decision for buyer (shipping failure)
	function resolveArbitration(bool arbitrationResult){
		if(msg.sender == auctionEscrow(owner).owner()){
			auctionEscrow casted = auctionEscrow(owner);
			if(arbitrationResult){
				casted.shippingSuccess(price,buyer,seller,ID,loc,shipping);
			}else{
				casted.shippingFailed(ID,price,buyer);
			}
			kill();
		}else{
			throw;
		}
	}
}

contract auctionEscrow is mortal {
	//ID to state
	//States:
	//0: Auction Live
	//1: Sold, unshipped
	//2: Shipping
	//3: Resolution
	//4: Concluded
	//5: Failed
	uint[] IDToState;
	
	mapping(uint => abstractAuction[5]) IDToAuction;
	uint public nextAuction;
	
	uint disputeResolutionPrice;
	
	//Initialization
	function auctionEscrow(uint _disputeResolutionPrice) {
		nextAuction = 0;
		disputeResolutionPrice = _disputeResolutionPrice;
	}
	
	//generate new auction
	function newAuction(address seller, uint minBid, uint lengthInHours) onlyOwner{
		auction a = new auction(seller,minBid,lengthInHours,nextAuction);
		IDToAuction[nextAuction][0] = a;
		IDToState[nextAuction] = 0;
		nextAuction++;
	}
	
	//auction ended
	function auctionEnded(uint maxBid, address maxBidder, address seller, uint ID){
		if(maxBidder == 0){
			//conclude auction, no bids occured
			IDToState[ID] = 5;
		}else{
			IDToState[ID] = 1;
			shippingManager sm = new shippingManager(maxBid,maxBidder,seller,ID);
			IDToAuction[ID][1] = sm;
		}
	}
	function shippingFailed(uint ID, uint price, address buyer){
		buyer.send(price);
		IDToState[ID] = 5;
	}
	
	function shippingInitiated(uint price, address buyer, address seller, uint ID, bytes32 loc, bytes32 shipping){
		IDToState[ID] = 2;
		hairTrigger trigger = new hairTrigger(price,buyer,seller,ID,loc,shipping);
		IDToAuction[ID][2] = trigger;
	}
	
	function shippingSuccess(uint price, address buyer, address seller, uint ID, bytes32 loc, bytes32 shipping){
		IDToState[ID] = 4;
		seller.send(price);
		finishedAuction a = new finishedAuction(price,buyer,seller,ID);
		IDToAuction[ID][4] = a;
	}
	
	function shippingFailure(uint price, address buyer, address seller, uint ID, bytes32 loc, bytes32 shipping, uint timegap){
		IDToState[ID] = 3;
		disputeResolution dr = new disputeResolution(price,buyer,seller,ID,loc,shipping,disputeResolutionPrice);
		IDToAuction[ID][3] = dr;
	}
	
	function getShippingInfo(uint ID) public returns(uint x, bytes32 a, bytes32 b){
		if(msg.sender == owner){
			uint stage = IDToState[ID];
			x = stage;
			if(stage == 0){
				a = "";
				b = "";
			}else if(stage >= 4){
				a = "";
				b = "";
			}else{
				auctionWithLocation auc = auctionWithLocation(IDToAuction[ID][stage]);
				(a,b) = auc.getShipInfo();
			}
		}else{
			throw;
		}
	}
	
	function killAll() onlyOwner{
		for(uint i = 0; i < nextAuction; i++){
			uint state = IDToState[i];
			if(state != 5){
				IDToAuction[i][state].kill();
			}
		}
	}
	
	function killClean(){
		killAll();
		suicide(owner);
	}
}