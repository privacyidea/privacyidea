import { Component, computed, inject, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatCardModule } from "@angular/material/card";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";

import { PoliciesService as PolicyService, PolicyAction } from "../../../services/policies/policies.service";
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
  // ===================================
  // 1. SERVICES
  // ===================================
  policyService: PolicyService = inject(PolicyService);

  // ===================================
  // 2. WRITABLE SIGNALS (STATE)
  // ===================================

  policyName = signal("");
  selectedScope = signal<string>("");
  currentActions = signal<any[]>([]);
  activeTab: WritableSignal<Tab> = signal("actions");
  actionValue: WritableSignal<string> = signal("");

  // ===================================
  // 3. SERVICE PROPERTIES / READONLY SIGNALS
  // ===================================

  actionFilter = this.policyService.actionFilter;
  policyActionsByGroupFiltered = this.policyService.policyActionsByGroupFiltered;

  // ===================================
  // 4. COMPUTED SIGNALS (DERIVED STATE)
  // ===================================

  policyActionGroupNames: Signal<string[]> = computed(() => {
    if (!this.selectedScope()) return [];
    return Object.keys(this.policyService.policyActionsByGroupFiltered()[this.selectedScope()]);
  });

  selectedAction: Signal<PolicyAction | null> = computed(() => {
    const actions = this.policyService.policyActions();
    const actionName = this.selectedActionName();
    const scope = this.selectedScope(); // Only check for actions[scope][actionName] if actions[scope] exists
    if (actionName && actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  });

  transformedActionValue = computed(() => {
    const action = this.selectedActionName();
    const value = this.actionValue();
    console.log(`Transforming action value for action: ${action} with value: ${value}`);
  });

  isAddActionValueProvided: Signal<boolean> = computed(() => {
    return true;
  });

  // ===================================
  // 5. LINKED SIGNALS
  // ===================================

  selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: this.policyActionGroupNames,
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  selectedActionName: WritableSignal<string> = linkedSignal({
    source: computed(() => this.getActionNamesOfGroup(this.selectedActionGroup())),
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  // ===================================
  // 6. HELPER METHODS
  // ===================================

  getActionNamesOfGroup(group: string): string[] {
    const actionsByGroup = this.policyService.policyActionsByGroupFiltered();
    const scope = this.selectedScope();

    if (scope && actionsByGroup[scope]) {
      return Object.keys(actionsByGroup[scope][group] || {});
    }
    return [];
  }

  getInputPlaceholder(): string {
    const type = this.selectedAction()?.type;
    if (!type) return "Value";
    if (type === "bool") return "true/false";
    if (type === "str") return "Text";
    if (type === "int") return "Number";
    return "Value";
  }

  // ===================================
  // 7. EVENT HANDLERS / ACTIONS
  // ===================================

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  onScopeSelect($event: string) {
    this.policyService.selectedScope.set($event);
    this.selectedScope.set($event);
  }

  addAction() {
    console.log("Selected Action: ", this.selectedAction());

    // Implementiere hier die Logik, um die Aktion zum Policy-Objekt hinzuzufügen
  }

  editAction(arg0: string) {}

  deleteAction(actionName: string): void {
    console.log(`Deleting action: ${actionName}`);

    // Implementiere hier die Logik, um die Aktion aus dem Policy-Objekt zu entfernen
  }

  savePolicy(matExpansionPanel: MatExpansionPanel) {
    console.log("Saving new policy");
    const selectedActionName = this.selectedActionName();
    const allActions = this.policyService.policyActions();

    this.transformedActionValue();

    // Implementiere hier die Logik, um das neue Policy zu speichern

    this.resetPolicy(matExpansionPanel);
  }

  resetPolicy(matExpansionPanel: MatExpansionPanel) {
    console.log("Resetting policy");
    this.selectedScope.set("");
    this.currentActions.set([]);
    this.policyName.set("");

    // Implementiere hier die Logik, um das Policy-Objekt zurückzusetzen

    matExpansionPanel.close();
  }
}
