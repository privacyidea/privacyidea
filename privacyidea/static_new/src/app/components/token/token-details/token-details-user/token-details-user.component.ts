import { NgClass } from "@angular/common";
import { Component, computed, inject, Input, signal, Signal, WritableSignal } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { MatCell, MatColumnDef, MatTableModule } from "@angular/material/table";
import {
  NotificationService,
  NotificationServiceInterface,
} from "../../../../services/notification/notification.service";
import {
  OverflowService,
  OverflowServiceInterface,
} from "../../../../services/overflow/overflow.service";
import { RealmService, RealmServiceInterface } from "../../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import {
  EditableElement,
  EditButtonsComponent,
} from "../../../shared/edit-buttons/edit-buttons.component";

@Component({
  selector: "app-token-details-user",
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatLabel,
    MatCell,
    MatFormField,
    MatInput,
    ReactiveFormsModule,
    MatAutocompleteTrigger,
    MatAutocomplete,
    MatOption,
    FormsModule,
    MatSelect,
    MatIconButton,
    MatIcon,
    EditButtonsComponent,
    NgClass,
    ClearableInputComponent,
  ],
  templateUrl: "./token-details-user.component.html",
  styleUrl: "./token-details-user.component.scss",
})
export class TokenDetailsUserComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly notificationService: NotificationServiceInterface =
    inject(NotificationService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);

  @Input() userData = signal<EditableElement[]>([]);
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  tokenType = computed(() => {
    const tokenDetail = this.tokenService.tokenDetailResource.value();
    return tokenDetail?.result?.value?.tokens?.[0].tokentype;
  });

  unassignUser() {
    this.tokenService.unassignUser(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenService.tokenDetailResource.reload();
      },
    });
  }

  toggleUserEdit(): void {
    this.isEditingUser.update((b) => !b);
    this.realmService.defaultRealmResource.reload();
  }

  cancelUserEdit(): void {
    this.isEditingUser.update((b) => !b);
    this.userService.userFilter.set("");
  }

  saveUser() {
    this.tokenService
      .assignUser({
        tokenSerial: this.tokenSerial(),
        username: this.userService.userNameFilter(),
        realm: this.userService.selectedUserRealm(),
      })
      .subscribe({
        next: () => {
          this.userService.userFilter.set("");
          this.userService.selectedUserRealm.set("");
          this.isEditingUser.update((b) => !b);
          this.tokenService.tokenDetailResource.reload();
        },
      });
  }
}
