import { Component, inject, signal } from "@angular/core";
import { MachineresolverPanelNewComponent } from "./machineresolver-panel-new/machineresolver-panel-new.component";
import { MachineresolverPanelEditComponent } from "./machineresolver-panel-edit/machineresolver-panel-edit.component";
import { MatExpansionModule } from "@angular/material/expansion";
import {
  MachineresolverService,
  MachineresolverServiceInterface
} from "../../services/machineresolver/machineresolver.service";

@Component({
  selector: "app-machineresolver",
  templateUrl: "./machineresolver.component.html",
  styleUrls: ["./machineresolver.component.scss"],
  imports: [MachineresolverPanelNewComponent, MachineresolverPanelEditComponent, MatExpansionModule]
})
export class MachineresolverComponent {
  machineresolverService: MachineresolverServiceInterface = inject(MachineresolverService);

  machineresolvers = this.machineresolverService.machineresolvers;
}
