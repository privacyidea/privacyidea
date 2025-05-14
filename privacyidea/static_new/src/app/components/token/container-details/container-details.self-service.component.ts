import { Component } from '@angular/core';
import { NgClass } from '@angular/common';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTableModule,
} from '@angular/material/table';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatListItem } from '@angular/material/list';
import { EditButtonsComponent } from '../../shared/edit-buttons/edit-buttons.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { ContainerDetailsInfoComponent } from './container-details-info/container-details-info.component';
import { ContainerDetailsTokenTableComponent } from './container-details-token-table/container-details-token-table.component';
import { MatPaginator } from '@angular/material/paginator';
import { MatDivider } from '@angular/material/divider';
import { MatCheckbox } from '@angular/material/checkbox';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { ContainerDetailsComponent } from './container-details.component';

@Component({
  selector: 'app-container-details-self-service',
  standalone: true,
  imports: [
    NgClass,
    MatLabel,
    MatTableModule,
    MatCell,
    MatColumnDef,
    MatRow,
    ReactiveFormsModule,
    MatListItem,
    EditButtonsComponent,
    MatFormField,
    FormsModule,
    MatSelectModule,
    MatInput,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatIcon,
    MatIconButton,
    ContainerDetailsInfoComponent,
    ContainerDetailsTokenTableComponent,
    MatPaginator,
    MatDivider,
    MatCheckbox,
    CopyButtonComponent,
  ],
  templateUrl: './container-details.self-service.component.html',
  styleUrls: ['./container-details.component.scss'],
})
export class ContainerDetailsSelfServiceComponent extends ContainerDetailsComponent {}
