export class TokenData {
  serial?: string;
  tokentype?: string;
  active?: boolean;
  description?: string;
  failcount?: number;
  rollout_state?: string;
  username?: string;
  user_realm?: string;
  realms?: string;
  container_serial?: string;
  revoked?: boolean;
  locked?: boolean;

  constructor(data: any) {
    this.serial = data.serial;
    this.tokentype = data.tokentype;
    this.active = data.active;
    this.description = data.description;
    this.failcount = data.failcount;
    this.rollout_state = data.rollout_state;
    this.username = data.username;
    this.user_realm = data.user_realm;
    this.realms = data.realms;
    this.container_serial = data.container_serial;
    this.revoked = data.revoked;
    this.locked = data.locked;
  }

  static parseList(tokens: any[]): TokenData[] {
    return tokens.map((token) => {
      return new TokenData(token);
    });
  }
}
