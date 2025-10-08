import { Component, Input, input, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { PolicyDetail } from "../../../services/policies/policies.service";
import { FormsModule } from "@angular/forms";
import { ActionSelectorComponent } from "../new-policy-panel/action-selector/action-selector.component";

type Tab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    FormsModule,
    ActionSelectorComponent
  ],
  templateUrl: "./policy-panel.component.html",
  styleUrl: "./policy-panel.component.scss"
})
export class PolicyPanelComponent {
  editAction(arg0: string) {}
  policy = input.required<PolicyDetail>();
  activeTab: WritableSignal<Tab> = signal("actions");
  @Input({ required: true }) isEditMode!: boolean;
  addActionValue: any;

  getActionsOfPolicy(policy: PolicyDetail): [string, unknown][] {
    if (!policy.action) return [];
    return Object.entries(policy.action);
  }

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  deleteAction(actionName: string): void {
    // Implementiere hier die Logik, um die Aktion aus dem Policy-Objekt zu entfernen
  }

  isAddActionValueProvided() {
    return false;
  }
}
