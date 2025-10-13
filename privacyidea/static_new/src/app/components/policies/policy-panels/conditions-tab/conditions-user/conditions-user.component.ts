import { Component, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { PolicyService as PolicyService } from "../../../../../services/policies/policies.service";
import { UserService } from "../../../../../services/user/user.service";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: "./conditions-user.component.html",
  styleUrls: ["./conditions-user.component.scss"]
})
export class ActionSelectorComponent {
  realmService: RealmServiceInterface = inject(RealmService);
  resolverService: ResolverService = inject(ResolverService);
  userResolver = this.resolverService.resol;
}
