export class ChallengeData {
  //   result: Object { status: true, value: {…} }
  // status: true
  // value: Object { count: 79, current: 0, next: 1, … }​
  // challenges: Array(10) [ {…}, {…}, {…}, … ]​​
  // 0: Object { challenge: "ENFFIYEKDXIK3W5MMABBDUJCPEVEXGU6", data: "60,69,52,69", expiration: "Thu, 05 Sep 2024 14:20:14 GMT", … }

  // challenge: "ENFFIYEKDXIK3W5MMABBDUJCPEVEXGU6"​​​
  // data: "60,69,52,69"​​​
  // expiration: "Thu, 05 Sep 2024 14:20:14 GMT"​​​
  // id: 70​​​
  // otp_received: false​​​
  // otp_valid: false​​​
  // received_count: 0​​​
  // serial: "PIPU0004405C"​​​
  // timestamp: "Thu, 05 Sep 2024 14:18:14 GMT"​​​
  // transaction_id: "10682940417790313753"​​​
  // <prototype>: Object { … }​​
  // 1: Object { challenge: "DQPCC3YARKILUKXYDPDA6VVPZTKYGUUW", data: "60,69,52,69", expiration: "Thu, 05 Sep 2024 14:20:14 GMT", … }​​
  // length: 10​​
  // <prototype>: Array []​
  // count: 79​
  // current: 0​
  // next: 1​
  // prev: null​
  // <prototype>: Object { … }
  // <prototype>: Object { … }

  // challenge: "ENFFIYEKDXIK3W5MMABBDUJCPEVEXGU6"
  // data: "60,69,52,69"
  // expiration: "Thu, 05 Sep 2024 14:20:14 GMT"
  // id: 70
  // otp_received: false
  // otp_valid: false
  // received_count: 0
  // serial: "PIPU0004405C"
  // timestamp: "Thu, 05 Sep 2024 14:18:14 GMT"
  // transaction_id: "10682940417790313753" }​​​
  constructor(
    public challenge: string,
    public data: string,
    public expiration: Date,
    public id: number,
    public otpReceived: boolean,
    public otpValid: boolean,
    public received_count: number,
    public serial: string,
    public timestamp: Date,
    public transactionId: string,
  ) {}

  static fromJson(json: any): ChallengeData {
    return new ChallengeData(
      json.challenge,
      json.data,
      new Date(json.expiration),
      json.id,
      json.otp_received,
      json.otp_valid,
      json.received_count,
      json.serial,
      new Date(json.timestamp),
      json.transaction_id,
    );
  }
  static parseList(json: any[]): ChallengeData[] {
    return json.map((data) => ChallengeData.fromJson(data));
  }
}
