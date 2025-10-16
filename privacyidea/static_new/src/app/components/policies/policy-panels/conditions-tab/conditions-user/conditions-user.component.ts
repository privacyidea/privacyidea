import {
  Component,
  computed,
  inject,
  signal,
  ViewChild,
  ChangeDetectorRef // Hinzugefügt
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button"; // Angenommen, Sie verwenden einen mat-button

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
    MatButtonModule
  ],
  templateUrl: "./conditions-user.component.html",
  styleUrl: "./conditions-user.component.scss"
})
export class ConditionsUserComponent {
  @ViewChild("resolverSelect") resolverSelect!: MatSelect;
  @ViewChild("realmSelect") realmSelect!: MatSelect;
  realmService: RealmServiceInterface = inject(RealmService);
  resolverService: ResolverService = inject(ResolverService);

  selectedRealms = signal<string[]>([]);
  selectedResolvers = signal<string[]>([]);
  selectedUsers = signal<string[]>([]);
  userCaseInsensitive = signal(false);

  selectRealm(realmNames: string[]): void {
    this.selectedRealms.set(realmNames);
    console.log("Selected realm:", realmNames);
  }

  selectResolver(resolverNames: string[]): void {
    this.selectedResolvers.set(resolverNames);
    console.log("Selected resolver:", resolverNames);
  }

  toggleAllRealms() {
    if (this.isAllRealmsSelected()) {
      this.selectedRealms.set([]);
    } else {
      const allRealms = this.realmService.realmOptions();
      this.selectedRealms.set([...allRealms]);
    }
    setTimeout(() => {
      this.realmSelect.close();
    });
  }

  toggleAllResolvers() {
    if (this.isAllResolversSelected()) {
      this.selectedResolvers.set([]);
    } else {
      const allResolvers = this.resolverService.resolverOptions();
      this.selectedResolvers.set([...allResolvers]);
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
    if (user && !this.selectedUsers().includes(user)) {
      this.selectedUsers.set([...this.selectedUsers(), user]);
    }
  }

  removeUser(user: string) {
    this.selectedUsers.set(this.selectedUsers().filter((u) => u !== user));
  }

  clearUsers() {
    this.selectedUsers.set([]);
  }
  toggleUserCaseInsensitive() {
    this.userCaseInsensitive.set(!this.userCaseInsensitive());
  }
}
