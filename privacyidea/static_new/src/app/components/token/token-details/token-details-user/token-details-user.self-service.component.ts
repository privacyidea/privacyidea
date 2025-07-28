import { NgClass } from '@angular/common';
import { Component, inject } from '@angular/core';
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
import {
  NotificationService,
  NotificationServiceInterface,
} from '../../../../services/notification/notification.service';
import {
  OverflowService,
  OverflowServiceInterface,
} from '../../../../services/overflow/overflow.service';
import {
  RealmService,
  RealmServiceInterface,
} from '../../../../services/realm/realm.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';
import {
  UserService,
  UserServiceInterface,
} from '../../../../services/user/user.service';
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
  protected override tokenService: TokenServiceInterface = inject(TokenService);
  protected override realmService: RealmServiceInterface = inject(RealmService);
  protected override userService: UserServiceInterface = inject(UserService);
  protected override notificationService: NotificationServiceInterface =
    inject(NotificationService);
  protected override overflowService: OverflowServiceInterface =
    inject(OverflowService);

  constructor() {
    super();
  }

  override canSetRandomPin() {
    console.warn('canSetRandomPin Method not implemented.');
    return false;
  }
}
