import { Component, inject } from '@angular/core';
import { NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';

import { MatCard, MatCardContent } from '@angular/material/card';
import { MatList, MatListItem } from '@angular/material/list';
import { MatIcon } from '@angular/material/icon';
import { MatButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';

import {
  OverflowService,
  OverflowServiceInterface,
} from '../../../services/overflow/overflow.service';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../services/version/version.service';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatSelect } from '@angular/material/select';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatOption } from '@angular/material/core';
import {
  RealmService,
  RealmServiceInterface,
} from '../../../services/realm/realm.service';
import {
  UserService,
  UserServiceInterface,
} from '../../../services/user/user.service';
import { ROUTE_PATHS } from '../../../app.routes';

@Component({
  selector: 'app-user-card',
  standalone: true,
  imports: [
    MatCard,
    MatCardContent,
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    MatDivider,
    RouterLink,
    NgClass,
    MatSelect,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    ReactiveFormsModule,
    FormsModule,
  ],
  templateUrl: './user-card.component.html',
  styleUrls: ['./user-card.component.scss'],
})
export class UserCardComponent {
  protected readonly overflowService: OverflowServiceInterface =
    inject(OverflowService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface =
    inject(VersioningService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  selectedUserRealmControl = new FormControl<string>(
    this.userService.selectedUserRealm(),
    { nonNullable: true },
  );
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
