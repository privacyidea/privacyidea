import { Component, computed, inject, signal, ViewChild } from "@angular/core";
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
  @ViewChild("nodeSelect") resolverSelect!: MatSelect;
  policyService: PolicyService = inject(PolicyService);
  systemService: SystemServiceInterface = inject(SystemService);
  selectedPolicy = this.policyService.selectedPolicy;
  selectedPolicyName = computed(() => this.selectedPolicy?.name || "");

  availablePinodesList = computed(() => this.systemService.nodes().map((node) => node.name));
  selectedPinodes = computed<string[]>(() => {
    console.log("Selected policy nodes:", this.selectedPolicy()?.pinode);
    return this.selectedPolicy()?.pinode || [];
  });

  addUserAgentFormControl = new FormControl<string>("");

  validTimeFormControl = new FormControl<string>("", this.validTimeValidator.bind(this));
  clientFormControl = new FormControl<string>("", this.clientValidator.bind(this));

  constructor() {
    this.validTimeFormControl.valueChanges.subscribe((value) => {
      if (!value) return;
      this.setValidTime(value);
    });

    this.clientFormControl.valueChanges.subscribe((value) => {
      if (!value) return;
      this.setClients(value);
    });
  }

  // Placeholder for available user agents
  availableUserAgents = signal<string[]>(["Mozilla Firefox", "Google Chrome", "Microsoft Edge"]);
  selectedUserAgents = computed(() => {
    console.log("Selected policy user agents:", this.selectedPolicy()?.user_agents);
    return this.selectedPolicy()?.user_agents || [];
  });
  isAllNodesSelected = computed(() => this.selectedPinodes().length === this.availablePinodesList().length);

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
      this.resolverSelect.close();
    });
  }

  addUserAgent(userAgent: string) {
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

  setValidTime(validTime: string) {
    // if (!this._validTimeIsCorrect(validTime)) return;
    this.policyService.updateSelectedPolicy({
      time: validTime
    });
  }

  setClients(clients: string) {
    if (!this._clientIsCorrect(clients)) return;
    const clientsArray = clients.split(",").map((c) => c.trim());
    this.policyService.updateSelectedPolicy({
      client: clientsArray
    });
  }

  validTimeValidator(control: AbstractControl): ValidationErrors | null {
    const validTime = control.value;
    if (!validTime) return null;
    console.log("Validating valid time:", validTime);
    if (this._validTimeIsCorrect(validTime)) {
      return null;
    }
    return {
      invalidValidTime: { value: control.value }
    };
  }
  _validTimeIsCorrect(validTime: string): boolean {
    //Mon-Fri: 9-18, Sat: 10-15 (2nd number is NOT optional)
    const regex =
      /^((Mon|Tue|Wed|Thu|Fri|Sat|Sun)(-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?:\s([0-1]?[0-9]|2[0-3])-([0-1]?[0-9]|2[0-3])(,\s)?)+$/;
    return validTime === "" || regex.test(validTime);
  }

  clientValidator(clientControl: AbstractControl): ValidationErrors | null {
    const client = clientControl.value;
    if (!client) return null;
    if (typeof client !== "string") return { invalidClient: { value: clientControl.value } };
    const isValid = this._clientIsCorrect(client);
    if (isValid) return null;
    return {
      invalidClient: { value: clientControl.value }
    };
  }
  _clientIsCorrect(client: string): boolean {
    const regex = /^(!?\d{1,3}(\.\d{1,3}){3}(\/\d{1,2})?)(,\s*!?\d{1,3}(\.\d{1,3}){3}(\/\d{1,2})?)*$/;
    return client === "" || regex.test(client);
  }

  userAgentValidator(control: AbstractControl): ValidationErrors | null {
    const userAgent = control.value;
    if (!userAgent) return null;
    if (this._userAgentIncludesComma(userAgent)) {
      return {
        includesComma: { value: control.value }
      };
    }
    return null;
  }

  _userAgentIncludesComma(userAgent: string): boolean {
    return userAgent.includes(",");
  }

  updateSelectedPinodes($event: MatSelectChange<string[]>) {
    this.policyService.updateSelectedPolicy({
      pinode: $event.value
    });
  }
}
