import { NgClass } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
  MatOption,
} from '@angular/material/autocomplete';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { MatCell, MatColumnDef, MatTableModule } from '@angular/material/table';
import { NotificationService } from '../../../../services/notification/notification.service';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { RealmService } from '../../../../services/realm/realm.service';
import { TokenService } from '../../../../services/token/token.service';
import { UiPolicyService } from '../../../../services/ui-policy/ui-policy.service';
import { UserService } from '../../../../services/user/user.service';
import { EditButtonsComponent } from '../../../shared/edit-buttons/edit-buttons.component';
import { TokenDetailsUserComponent } from './token-details-user.component';

@Component({
  selector: 'app-token-details-user',
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
    MatDivider,
    MatFabButton,
    EditButtonsComponent,
    NgClass,
  ],
  templateUrl: './token-details-user.self-service.component.html',
  styleUrl: './token-details-user.component.scss',
})
export class TokenDetailsUserSelfServiceComponent extends TokenDetailsUserComponent {
  constructor(
    protected override tokenService: TokenService,
    protected override realmService: RealmService,
    protected override userService: UserService,
    protected override notificationService: NotificationService,
    protected override overflowService: OverflowService,
    protected override uiPolicyService: UiPolicyService,
  ) {
    super(
      tokenService,
      realmService,
      userService,
      notificationService,
      overflowService,
      uiPolicyService,
    );
  }

  override canSetRandomPin() {
    console.log(
      'Policy for setting random PIN:',
      this.uiPolicyService.otpPinSetRandomUser,
    );
    return false; // Placeholder for actual implementation
  }
}
