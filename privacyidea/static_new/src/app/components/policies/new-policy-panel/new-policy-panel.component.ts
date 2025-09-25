import { Component, inject, Input, input, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { PoliciesService, PolicyDetail } from "../../../services/policies/policies.service";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { HorizontalWheelComponent } from "../../shared/horizontal-wheel/horizontal-wheel.component";

type Tab = "actions" | "conditions";

@Component({
  selector: "app-new-policy-panel",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    FormsModule,
    MatExpansionModule,
    HorizontalWheelComponent
  ],
  templateUrl: "./new-policy-panel.component.html",
  styleUrl: "./new-policy-panel.component.scss"
})
export class NewPolicyPanelComponent {
  scope = signal<"" | "admin" | "system" | "authentication" | "selfservice">("");
  actions = signal([]);

  policiesService = inject(PoliciesService);

  editAction(arg0: string) {}
  activeTab: WritableSignal<Tab> = signal("actions");

  addActionValue: any;

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
  onScopeSelect($event: any) {
    this.scope.set($event);
  }
  addAction(action: string) {
    console.log(`Adding action: ${action}`);
    // Implementiere hier die Logik, um die Aktion zum Policy-Objekt hinzuzufügen
  }
  resetPolicy(matExpansionPanel: MatExpansionPanel) {
    console.log("Resetting policy");
    this.scope.set("");
    this.actions.set([]);
    // Implementiere hier die Logik, um das Policy-Objekt zurückzusetzen

    matExpansionPanel.close();
  }
  savePolicy() {
    console.log("Saving new policy");
    // Implementiere hier die Logik, um das neue Policy zu speichern
  }
}
