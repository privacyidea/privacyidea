import { signal } from "@angular/core";
import { PiNode, SystemServiceInterface } from "../../app/services/system/system.service";

export class MockSystemService implements SystemServiceInterface {
  nodes = signal<PiNode[]>([]);
  systemConfig = signal({});
}
