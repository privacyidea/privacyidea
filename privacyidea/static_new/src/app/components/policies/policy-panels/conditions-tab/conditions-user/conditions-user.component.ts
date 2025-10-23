import { Component, computed, inject, input, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import {
  AbstractControl,
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn
} from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService } from "../../../../../services/policies/policies.service";

@Component({
  selector: "app-conditions-user",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatButtonModule,
    MatExpansionModule,
    ReactiveFormsModule
  ],
  templateUrl: "./conditions-user.component.html",
  styleUrl: "./conditions-user.component.scss"
})
export class ConditionsUserComponent {
  @ViewChild("resolverSelect") resolverSelect!: MatSelect;
  @ViewChild("realmSelect") realmSelect!: MatSelect;
  isEditMode = input.required<boolean>();
  realmService: RealmServiceInterface = inject(RealmService);
  resolverService: ResolverService = inject(ResolverService);
  policyService = inject(PolicyService);

  selectedRealms = computed(() => this.policyService.selectedPolicy()?.realm || []);
  selectedResolvers = computed(() => this.policyService.selectedPolicy()?.resolver || []);
  selectedUsers = computed(() => this.policyService.selectedPolicy()?.user || []);
  userCaseInsensitive = computed(() => this.policyService.selectedPolicy()?.user_case_insensitive || false);

  userFormControl = new FormControl<string>("", this.userValidator.bind(this));

  selectRealm(realmNames: string[]): void {
    this.policyService.updateSelectedPolicy({ realm: realmNames });
    console.log("Selected realm:", realmNames);
  }

  selectResolver(resolverNames: string[]): void {
    this.policyService.updateSelectedPolicy({ resolver: resolverNames });
    console.log("Selected resolver:", resolverNames);
  }

  toggleAllRealms() {
    if (this.isAllRealmsSelected()) {
      this.policyService.updateSelectedPolicy({ realm: [] });
    } else {
      const allRealms = this.realmService.realmOptions();
      this.policyService.updateSelectedPolicy({ realm: allRealms });
    }
    setTimeout(() => {
      this.realmSelect.close();
    });
  }

  toggleAllResolvers() {
    if (this.isAllResolversSelected()) {
      this.policyService.updateSelectedPolicy({ resolver: [] });
    } else {
      const allResolvers = this.resolverService.resolverOptions();
      this.policyService.updateSelectedPolicy({ resolver: allResolvers });
    }
    setTimeout(() => {
      this.resolverSelect.close();
    });
  }

  isAllRealmsSelected = computed(() => this.selectedRealms().length === this.realmService.realmOptions().length);

  isAllResolversSelected = computed(
    () => this.selectedResolvers().length === this.resolverService.resolverOptions().length
  );

  addUser(user: string) {
    console.log("Adding user:", user);
    if (this.userFormControl.invalid) {
      return;
    }
    if (user && !this.selectedUsers().includes(user)) {
      this.policyService.updateSelectedPolicy({ user: [...this.selectedUsers(), user] });
    }
  }

  removeUser(user: string) {
    this.policyService.updateSelectedPolicy({ user: this.selectedUsers().filter((u) => u !== user) });
  }

  clearUsers() {
    this.policyService.updateSelectedPolicy({ user: [] });
  }
  toggleUserCaseInsensitive() {
    this.policyService.updateSelectedPolicy({ user_case_insensitive: !this.userCaseInsensitive() });
  }

  userValidator(control: AbstractControl): ValidationErrors | null {
    return /[,]/.test(control.value) ? { includesComma: { value: control.value } } : null;
  }
}
