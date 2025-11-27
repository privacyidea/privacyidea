import { Component, input, Input } from "@angular/core";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { Machineresolver } from "../../../services/machineresolver/machineresolver.service";

@Component({
  selector: "app-machineresolver-panel-edit",
  templateUrl: "./machineresolver-panel-edit.component.html",
  styleUrls: ["./machineresolver-panel-edit.component.scss"],
  imports: [MatExpansionModule, MatIconModule]
})
export class MachineresolverPanelEditComponent {
  machineresolver = input.required<Machineresolver>();
}
