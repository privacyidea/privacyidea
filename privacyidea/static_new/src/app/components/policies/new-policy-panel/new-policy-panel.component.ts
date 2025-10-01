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
import { ActionSelectorComponent } from "./action-selector/action-selector.component";
import { ActionDetailComponent } from "./action-detail/action-detail.component";
import { SelectedActionsListComponent } from "./selected-actions-list/selected-actions-list.component";

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
    HorizontalWheelComponent,
    ActionSelectorComponent,
    ActionDetailComponent,
    SelectedActionsListComponent
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

  activeTab: WritableSignal<Tab> = signal("actions");

  // ===================================
  // 3. COMPUTED SIGNALS (DERIVED STATE)
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

  // ===================================
  // 4. LINKED SIGNALS
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
    source: computed(() => this.getActionNamesOfGroup(this.selectedActionGroup()) ?? []),
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  // ===================================
  // 5. HELPER METHODS
  // ===================================

  getActionNamesOfGroup(group: string): string[] {
    const actionsByGroup = this.policyService.policyActionsByGroupFiltered();
    const scope = this.selectedScope();

    if (scope && actionsByGroup[scope]) {
      return Object.keys(actionsByGroup[scope][group] || {});
    }
    return [];
  }

  // ===================================
  // 6. EVENT HANDLERS / ACTIONS
  // ===================================

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  onScopeSelect($event: string) {
    this.policyService.selectedScope.set($event);
    this.selectedScope.set($event);
  }

  onAddAction(event: { actionName: string; value: string }) {
    if (this.policyService.alreadyAddedActionNames().includes(event.actionName)) return;

    const newAction = {
      actionName: event.actionName,
      value: event.value
    };

    const updatedActions = [...this.policyService.currentActions(), newAction];
    this.policyService.currentActions.set(updatedActions);
  }

  editAction(arg0: string) {}

  deleteAction(actionName: string): void {
    console.info(`Deleting action: ${actionName}`);
    const updatedActions = this.policyService.currentActions().filter((a) => a.actionName !== actionName);
    this.policyService.currentActions.set(updatedActions);
  }

  savePolicy(matExpansionPanel: MatExpansionPanel) {
    console.info("Saving new policy");
    // Implementiere hier die Logik, um das neue Policy zu speichern
    this.resetPolicy(matExpansionPanel);
  }

  resetPolicy(matExpansionPanel: MatExpansionPanel) {
    console.info("Resetting policy");
    this.selectedScope.set("");
    this.policyService.currentActions.set([]);
    this.policyName.set("");
    Object.entries(this.policyService.currentActions());
    // Implementiere hier die Logik, um das Policy-Objekt zurückzusetzen

    matExpansionPanel.close();
  }
}
