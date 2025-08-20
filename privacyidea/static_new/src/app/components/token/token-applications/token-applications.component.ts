import { Component, inject } from "@angular/core";
import { MatSelectModule } from "@angular/material/select";
import { MachineService, MachineServiceInterface } from "../../../services/machine/machine.service";
import { TokenApplicationsOfflineComponent } from "./token-applications-offline/token-applications-offline.component";
import { TokenApplicationsSshComponent } from "./token-applications-ssh/token-applications-ssh.component";

@Component({
  selector: "app-token-applications",
  standalone: true,
  imports: [
    TokenApplicationsSshComponent,
    TokenApplicationsOfflineComponent,
    MatSelectModule
  ],
  templateUrl: "./token-applications.component.html",
  styleUrls: ["./token-applications.component.scss"]
})
export class TokenApplicationsComponent {
  private readonly machineService: MachineServiceInterface =
    inject(MachineService);

  selectedApplicationType = this.machineService.selectedApplicationType;
}
