import { Component, computed, inject, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatCardModule } from "@angular/material/card";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import { PolicyService } from "../../../services/policies/policies.service";
import { HorizontalWheelComponent } from "../../shared/horizontal-wheel/horizontal-wheel.component";
import { ActionSelectorComponent } from "./action-selector/action-selector.component";
import { ActionDetailComponent } from "./action-detail/action-detail.component";
import { SelectedActionsListComponent } from "./selected-actions-list/selected-actions-list.component";
import { PolicyDescriptionComponent } from "./policy-description/policy-description.component";

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
    SelectedActionsListComponent,
    PolicyDescriptionComponent
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

  policyName = computed(() => this.policyService.selectedPolicy()?.name);
  policyScope = computed(() => this.policyService.selectedPolicy()?.scope);
  selectedPolicyHasActions = computed(() => {
    const policy = this.policyService.selectedPolicy();
    if (!policy) return false;
    return policy?.action && Object.keys(policy.action).length > 0;
  });

  // ===================================
  // 3. WRITABLE SIGNALS (STATE)
  // ===================================

  activeTab: WritableSignal<Tab> = signal("actions");

  // ===================================
  // 4. EVENT HANDLERS / ACTIONS
  // ===================================

  setActiveTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  onScopeSelect($event: string) {
    const selectedPolicy = this.policyService.selectedPolicy();
    if (!selectedPolicy) return;
    const updatedPolicy = {
      ...selectedPolicy,
      scope: $event
    };
    console.log("onScopeSelect: ", $event);
    this.policyService.selectedPolicy.set(updatedPolicy);
  }

  savePolicy(matExpansionPanel: MatExpansionPanel) {
    // Implementiere hier die Logik, um das neue Policy zu speichern
    this.policyService.deselectPolicy();
    matExpansionPanel.close();
  }
  resetPolicy(matExpansionPanel: MatExpansionPanel) {
    this.policyService.deselectPolicy();
    matExpansionPanel.close();
  }
}
