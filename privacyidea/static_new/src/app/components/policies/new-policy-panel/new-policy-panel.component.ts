import { Component, computed, inject, Input, input, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import {
  PoliciesService as PolicyService,
  PolicyDetail,
  PoliciesServiceInterface as PolicyServiceInterface,
  PolicyActionGroups,
  PolicyAction
} from "../../../services/policies/policies.service";
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
  selectAction(actionName: string) {
    console.log(`Selected action: ${actionName}`);
  }
  policyActionGroupNames: Signal<string[]> = computed(() => {
    if (!this.scope()) return [];
    return Object.keys(this.policyService.policyActionsByGroupFiltered()[this.scope()]);
  });
  selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: this.policyActionGroupNames,
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  getActionNamesOfGroup(group: string): string[] {
    if (this.scope() && this.policyService.policyActionsByGroupFiltered()[this.scope()]) {
      return Object.keys(this.policyService.policyActionsByGroupFiltered()[this.scope()][group] || {});
    }
    return [];
  }

  name = signal("");
  scope = signal<string>("");
  actions = signal([]);

  policyService: PolicyService = inject(PolicyService); // PolicyServiceInterface = inject(PolicyService); // <- use the interface later

  editAction(arg0: string) {}
  activeTab: WritableSignal<Tab> = signal("actions");

  actionFilter = this.policyService.actionFilter;
  policyActionsByGroupFiltered = this.policyService.policyActionsByGroupFiltered;

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
    this.policyService.selectedScope.set($event);
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
    this.name.set("");
    // Implementiere hier die Logik, um das Policy-Objekt zurückzusetzen

    matExpansionPanel.close();
  }
  savePolicy(matExpansionPanel: MatExpansionPanel) {
    console.log("Saving new policy");
    // Implementiere hier die Logik, um das neue Policy zu speichern

    this.resetPolicy(matExpansionPanel);
  }
}
