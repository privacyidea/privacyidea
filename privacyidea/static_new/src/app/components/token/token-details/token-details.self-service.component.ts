import { Component } from '@angular/core';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTable,
  MatTableModule,
} from '@angular/material/table';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatListItem } from '@angular/material/list';
import { NgClass } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatInput } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { TokenDetailsUserComponent } from './token-details-user/token-details-user.component';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { TokenDetailsInfoComponent } from './token-details-info/token-details-info.component';
import { TokenDetailsActionsComponent } from './token-details-actions/token-details-actions.component';
import { EditButtonsComponent } from '../../shared/edit-buttons/edit-buttons.component';
import { MatDivider } from '@angular/material/divider';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { TokenDetailsComponent } from './token-details.component';

@Component({
  selector: 'app-token-details-self-service',
  standalone: true,
  imports: [
    MatCell,
    MatTableModule,
    MatColumnDef,
    MatIcon,
    MatListItem,
    MatRow,
    MatTable,
    NgClass,
    FormsModule,
    MatInput,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatIconButton,
    TokenDetailsUserComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    EditButtonsComponent,
    MatDivider,
    CopyButtonComponent,
  ],
  templateUrl: './token-details.self-service.component.html',
  styleUrls: ['./token-details.component.scss'],
})
export class TokenDetailsSelfServiceComponent extends TokenDetailsComponent {}
