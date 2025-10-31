import { Component, computed, inject, input, signal, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import { AbstractControl, FormControl, FormsModule, ValidationErrors, ReactiveFormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { SystemServiceInterface, SystemService } from "../../../../../services/system/system.service";

@Component({
  selector: "app-conditions-nodes",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatFormFieldModule,
    MatExpansionModule,
    ReactiveFormsModule
  ],
  templateUrl: "./conditions-nodes.component.html",
  styleUrl: "./conditions-nodes.component.scss"
})
export class ConditionsNodesComponent {
  @ViewChild("nodeSelect") nodeSelect!: MatSelect;
  policyService: PolicyService = inject(PolicyService);
  systemService: SystemServiceInterface = inject(SystemService);
  selectedPolicy = this.policyService.selectedPolicy;
  selectedPolicyName = computed(() => this.selectedPolicy?.name || "");

  isEditMode = this.policyService.isEditMode;
  availablePinodesList = computed(() => this.systemService.nodes().map((node) => node.name));
  selectedPinodes = computed<string[]>(() => {
    console.log("Selected policy nodes:", this.selectedPolicy()?.pinode);
    return this.selectedPolicy()?.pinode || [];
  });

  selectedUserAgents = computed(() => this.policyService.selectedPolicy()?.user_agents || []);
  addUserAgentFormControl = new FormControl<string>("", this.userAgentValidator.bind(this));
  selectedValidTime = computed(() => this.policyService.selectedPolicy()?.time || "");
  validTimeFormControl = new FormControl<string>("", this.validTimeValidator.bind(this));
  selectedClient = computed(() => this.policyService.selectedPolicy()?.client || "");
  clientFormControl = new FormControl<string>("", this.clientValidator.bind(this));

  // Placeholder for available user agents
  availableUserAgents = signal<string[]>(["Mozilla Firefox", "Google Chrome", "Microsoft Edge"]);
  isAllNodesSelected = computed(() => this.selectedPinodes().length === this.availablePinodesList().length);

  constructor() {
    this.validTimeFormControl.valueChanges.subscribe(() => {
      this.setValidTime();
    });

    this.clientFormControl.valueChanges.subscribe(() => {
      this.setClients();
    });
  }

  toggleAllNodes() {
    if (this.isAllNodesSelected()) {
      this.policyService.updateSelectedPolicy({
        pinode: []
      });
    } else {
      this.policyService.updateSelectedPolicy({
        pinode: [...this.availablePinodesList()]
      });
    }
    setTimeout(() => {
      this.nodeSelect.close();
    });
  }

  addUserAgent() {
    if (this.addUserAgentFormControl.invalid) return;
    const userAgent = this.addUserAgentFormControl.value;
    if (!userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (oldUserAgents.includes(userAgent)) return;
    const newUserAgents = [...oldUserAgents, userAgent];
    console.log("Adding user agent:", newUserAgents);
    this.policyService.updateSelectedPolicy({
      user_agents: newUserAgents
    });
  }

  removeUserAgent(userAgent: string) {
    const newUserAgents = this.selectedUserAgents().filter((ua) => ua !== userAgent);
    this.policyService.updateSelectedPolicy({
      user_agents: newUserAgents
    });
  }
  clearUserAgents() {
    this.policyService.updateSelectedPolicy({ user_agents: [] });
  }

  setValidTime() {
    if (this.validTimeFormControl.invalid) {
      this.policyService.updateSelectedPolicy({
        time: ""
      });
      return;
    }
    const validTime = this.validTimeFormControl.value;
    if (!validTime) return;
    console.log("Setting valid time:", validTime);
    this.policyService.updateSelectedPolicy({
      time: validTime
    });
  }

  setClients() {
    if (this.clientFormControl.invalid) {
      this.policyService.updateSelectedPolicy({
        client: []
      });
      return;
    }
    const client = this.clientFormControl.value;
    if (!client) return;
    console.log("Setting clients:", client);
    const clientsArray = client.split(",").map((c) => c.trim());
    this.policyService.updateSelectedPolicy({
      client: clientsArray
    });
  }

  validTimeValidator(control: AbstractControl): ValidationErrors | null {
    const validTime = control.value;
    if (!validTime) return null;
    console.log("Validating valid time:", validTime);
    const regex =
      /^((Mon|Tue|Wed|Thu|Fri|Sat|Sun)(-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?:\s([0-1]?[0-9]|2[0-3])-([0-1]?[0-9]|2[0-3])(,\s)?)+$/;
    if (validTime === "" || regex.test(validTime)) {
      return null;
    }
    return {
      invalidValidTime: { value: control.value }
    };
  }

  clientValidator(clientControl: AbstractControl): ValidationErrors | null {
    const client = clientControl.value;
    if (!client) return null;
    if (typeof client !== "string") return { invalidClient: { value: clientControl.value } };
    const regex = /^(!?\d{1,3}(\.\d{1,3}){3}(\/\d{1,2})?)(,\s*!?\d{1,3}(\.\d{1,3}){3}(\/\d{1,2})?)*$/;
    const isValid = client === "" || regex.test(client);
    if (isValid) return null;
    return {
      invalidClient: { value: clientControl.value }
    };
  }

  userAgentValidator(control: AbstractControl): ValidationErrors | null {
    const userAgent = control.value;
    if (!userAgent) return null;
    if (userAgent.includes(",")) {
      return {
        includesComma: { value: control.value }
      };
    }
    return null;
  }

  updateSelectedPinodes($event: MatSelectChange<string[]>) {
    this.policyService.updateSelectedPolicy({
      pinode: $event.value
    });
  }
}
