import { Component, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { PolicyService as PolicyService } from "../../../../../services/policies/policies.service";
import { BoolSelectButtonsComponent } from "../selector-buttons/selector-buttons.component";

import { MatTooltipModule } from "@angular/material/tooltip";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    BoolSelectButtonsComponent,
    MatTooltipModule
  ],
  templateUrl: "./action-selector.component.html",
  styleUrls: ["./action-selector.component.scss"]
})
export class ActionSelectorComponent {
  // Services
  policyService = inject(PolicyService);
}
