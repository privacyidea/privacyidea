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

  policyName = computed(() => this.policyService._selectedPolicy()?.name);
  policyScope = computed(() => this.policyService._selectedPolicy()?.scope);

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
    const selectedPolicy = this.policyService._selectedPolicy();
    if (!selectedPolicy) return;
    const updatedPolicy = {
      ...selectedPolicy,
      scope: $event
    };
    console.log("onScopeSelect: ", $event);
    this.policyService._selectedPolicy.set(updatedPolicy);
  }

  onNameChange($event: string) {
    console.log("onNameChange: ", $event);
    this.policyService.updateSelectedPolicy({ name: $event });
  }

  savePolicy(matExpansionPanel: MatExpansionPanel) {
    // Implementiere hier die Logik, um das neue Policy zu speichern
    this.policyService.saveSelectedPolicy();
    this.policyService.deselectPolicy();
    matExpansionPanel.close();
  }
  resetPolicy(matExpansionPanel: MatExpansionPanel) {
    if (this.policyService.isPolicyEdited()) {
      if (confirm("Are you sure you want to discard the new policy? All changes will be lost.")) {
        this.policyService.deselectPolicy();
        matExpansionPanel.close();
      }
    } else {
      this.policyService.deselectPolicy();
      matExpansionPanel.close();
    }
  }

  canSavePolicy(): boolean {
    return this.policyService.canSaveSelectedPolicy();
  }
}
