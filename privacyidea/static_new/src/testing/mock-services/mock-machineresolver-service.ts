import { signal } from "@angular/core";
import { MachineresolverServiceInterface } from "../../app/services/machineresolver/machineresolver.service";

export class MockMachineresolverService implements MachineresolverServiceInterface {
  allMachineresolverTypes = ["hosts", "ldap"];
  machineresolvers = signal([]);
  postMachineresolver = jest.fn().mockResolvedValue(null);
  postTestMachineresolver = jest.fn().mockResolvedValue(null);
  deleteMachineresolver = jest.fn().mockResolvedValue(null);
}
