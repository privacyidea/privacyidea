import { Component, Input, input, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { PolicyDetail } from "../../../services/policies/policies.service";
import { FormsModule } from "@angular/forms";

type Tab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel",
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule, MatButtonToggleModule, FormsModule],
  templateUrl: "./policy-panel.component.html",
  styleUrl: "./policy-panel.component.scss"
})
export class PolicyPanelComponent {
  editAction(arg0: string) {}
  policy = input.required<PolicyDetail>();
  activeTab: WritableSignal<Tab> = signal("actions");
  @Input({ required: true }) isEditMode!: boolean;
  addActionValue: any;

  getActionsOfPolicy(): [string, unknown][] {
    return Object.entries(this.policy().action);
  }

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  deleteAction(actionName: string): void {
    console.log(`Deleting action: ${actionName}`);
    // Implementiere hier die Logik, um die Aktion aus dem Policy-Objekt zu entfernen
  }

  isAddActionValueProvided() {
    return false;
  }
}
