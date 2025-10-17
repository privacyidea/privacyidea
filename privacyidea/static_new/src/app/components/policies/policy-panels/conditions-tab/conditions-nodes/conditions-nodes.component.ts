import { Component, computed, signal, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";

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
    MatFormFieldModule
  ],
  templateUrl: "./conditions-nodes.component.html",
  styleUrl: "./conditions-nodes.component.scss"
})
export class ConditionsNodesComponent {
  @ViewChild("nodeSelect") resolverSelect!: MatSelect;
  availableNodes = signal<string[]>(["node1", "node2", "node3"]);
  selectedNodes = signal<string[]>([]);

  validTime = signal<string>("");
  client = signal<string>("");

  // Placeholder for available user agents
  availableUserAgents = signal<string[]>(["Mozilla Firefox", "Google Chrome", "Microsoft Edge"]);
  selectedUserAgents = signal<string[]>([]);

  isAllNodesSelected = computed(() => this.selectedNodes().length === this.availableNodes().length);

  toggleAllNodes() {
    if (this.isAllNodesSelected()) {
      this.selectedNodes.set([]);
    } else {
      this.selectedNodes.set([...this.availableNodes()]);
    }
    setTimeout(() => {
      this.resolverSelect.close();
    });
  }

  addUserAgent(userAgent: string) {
    if (userAgent && !this.selectedUserAgents().includes(userAgent)) {
      this.selectedUserAgents.set([...this.selectedUserAgents(), userAgent]);
    }
  }

  removeUserAgent(userAgent: string) {
    this.selectedUserAgents.set(this.selectedUserAgents().filter((ua) => ua !== userAgent));
  }

  setValidTime($event: string) {
    this.validTime.set($event);
  }

  validTimeValidator = computed((): boolean => {
    //Mon-Fri: 9-18, Sat: 10-15
    const regex =
      /^((Mon|Tue|Wed|Thu|Fri|Sat|Sun)(-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?:\s*(\d{1,2}(-\d{1,2})?)(,\s*(\d{1,2}(-\d{1,2})?))*\s*)+$/;
    return this.validTime() === "" || regex.test(this.validTime());
  });

  clientValidator = computed((): boolean => {
    //Please enter a valid client format, e.g., 10.0.0.0/8, !10.0.0.124
    const regex = /^(!?\d{1,3}(\.\d{1,3}){3}(\/\d{1,2})?)(,\s*!?\d{1,3}(\.\d{1,3}){3}(\/\d{1,2})?)*$/;
    const isValid = this.client() === "" || regex.test(this.client());
    console.log("isValid client:", isValid);
    return isValid;
  });
  clearUserAgents() {
    this.selectedUserAgents.set([]);
  }
}
