export class MachineTokenData {
  application?: string;
  id?: number;
  machine_id?: string;
  options?: MachineTokenOptions;
  resolver?: string;
  serial?: string;
  type?: string;

  constructor(data: any) {
    this.application = data.application;
    this.id = data.id;
    this.machine_id = data.machine_id;
    this.options = data.options;
    this.resolver = data.resolver;
    this.serial = data.serial;
    this.type = data.type;
  }

  static parseList(data: any[]): MachineTokenData[] {
    return data.map((sshToken) => new MachineTokenData(sshToken));
  }
}
export type MachineTokenOptions = {
  service_id?: string;
  user?: string;
};
