import { Component, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";

@Component({
  selector: "app-conditions-user",
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: "./conditions-user.component.html",
  styleUrls: ["./conditions-user.component.scss"]
})
export class ConditionsUserComponent {
  realmService: RealmServiceInterface = inject(RealmService);
  resolverService: ResolverService = inject(ResolverService);
  userResolver = this.resolverService.resolvers;

  selectedRealm = signal("");
  selectRealm(reamName: string) {
    this.selectedRealm.set(reamName);
  }
}
