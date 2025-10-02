import { Component, EventEmitter, inject, Input, Output } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { PolicyService } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-selected-actions-list",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: "./selected-actions-list.component.html",
  styleUrls: ["./selected-actions-list.component.scss"]
})
export class SelectedActionsListComponent {
  policyService = inject(PolicyService);

  @Input() actions: { actionName: string; value: string }[] = [];

  @Output() deleteAction = new EventEmitter<string>();
}
