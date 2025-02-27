export class ContainerData {
  serial?: string;
  type?: string;
  states?: string[];
  description?: string;
  users?: UserData[];
  user_realm?: string;
  realms?: string;

  constructor(data: any) {
    this.serial = data.serial;
    this.type = data.type;
    this.states = data.states;
    this.description = data.description;
    this.users = data.users;
    this.user_realm = data.user_realm;
    this.realms = data.realms;
  }

  static parseList(data: any[]): ContainerData[] {
    return data.map((item) => new ContainerData(item));
  }
}

class UserData {
  user_id: string;
  user_name: string;
  user_realm: string;
  user_resolver: string;

  constructor(data: any) {
    this.user_id = data.user_id;
    this.user_name = data.user_name;
    this.user_realm = data.user_realm;
    this.user_resolver = data.user_resolver;
  }

  static parseList(data: any[]): UserData[] {
    return data.map((item) => new UserData(item));
  }
}
