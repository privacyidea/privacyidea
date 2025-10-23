import { Component, computed, inject, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatCardModule } from "@angular/material/card";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { PolicyService } from "../../../../services/policies/policies.service";
import { HorizontalWheelComponent } from "../../../shared/horizontal-wheel/horizontal-wheel.component";
import { ActionTabComponent } from "../action-tab/action-tab.component";
import { ConditionsTabComponent } from "../conditions-tab/conditions-tab.component";

export type Tab = "actions" | "conditions";

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
    ActionTabComponent,
    ConditionsTabComponent
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
  // 2. COMPUTED SIGNALS
  // ===================================

  newPolicyName = computed(() => {
    if (this.policyService.viewMode() !== "new") return "";
    return this.policyService.selectedPolicyOriginal()?.name || "";
  });
  newPolicyScope = computed(() => {
    if (this.policyService.viewMode() !== "new") return "";
    return this.policyService.selectedPolicy()?.scope || "";
  });

  // ===================================
  // 3. WRITABLE SIGNALS (STATE)
  // ===================================

  activeTab: WritableSignal<Tab> = signal("actions");

  // ===================================
  // 4. EVENT HANDLERS / ACTIONS
  // ===================================

  canSavePolicy(): boolean {
    return this.policyService.canSaveSelectedPolicy();
  }

  onNameChange($event: string) {
    this.policyService.updateSelectedPolicy({ name: $event });
  }

  onScopeSelect($event: string) {
    this.policyService.updateSelectedPolicy({ scope: $event });
  }

  resetPolicy(matExpansionPanel: MatExpansionPanel) {
    if (this.policyService.isPolicyEdited()) {
      if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
        this.policyService.deselectPolicy(this.newPolicyName());
        matExpansionPanel.close();
      }
    } else {
      this.policyService.deselectPolicy(this.newPolicyName());
      matExpansionPanel.close();
    }
  }

  savePolicy(matExpansionPanel: MatExpansionPanel) {
    // Implementiere hier die Logik, um das neue Policy zu speichern
    this.policyService.savePolicyEdits();
    this.policyService.deselectPolicy(this.newPolicyName());
    matExpansionPanel.close();
  }

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }
}
