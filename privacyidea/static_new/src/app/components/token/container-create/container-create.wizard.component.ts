import { Component } from '@angular/core';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { MatInput } from '@angular/material/input';
import { MatCheckbox } from '@angular/material/checkbox';
import { ContainerCreateComponent } from './container-create.component';
import { AsyncPipe } from '@angular/common';
import { map } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer } from '@angular/platform-browser';
import { MatDialog } from '@angular/material/dialog';
import { VersionService } from '../../../services/version/version.service';
import { UserService } from '../../../services/user/user.service';
import { RealmService } from '../../../services/realm/realm.service';
import { ContainerService } from '../../../services/container/container.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { TokenService } from '../../../services/token/token.service';
import { ContentService } from '../../../services/content/content.service';

@Component({
  selector: 'app-container-create-wizard',
  imports: [
    MatButton,
    MatFormField,
    MatHint,
    MatIcon,
    MatOption,
    MatSelect,
    FormsModule,
    MatInput,
    MatLabel,
    MatCheckbox,
    MatIconButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionPanelHeader,
    AsyncPipe,
  ],
  templateUrl: './container-create.wizard.component.html',
  styleUrl: './container-create.component.scss',
})
export class ContainerCreateWizardComponent extends ContainerCreateComponent {
  readonly preTopHtml$ = this.http
    .get('/customize/container-create.wizard.pre.top.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly preBottomHtml$ = this.http
    .get('/customize/container-create.wizard.pre.bottom.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    registrationDialog: MatDialog,
    versioningService: VersionService,
    userService: UserService,
    realmService: RealmService,
    containerService: ContainerService,
    notificationService: NotificationService,
    tokenService: TokenService,
    contentService: ContentService,
  ) {
    super(
      registrationDialog,
      versioningService,
      userService,
      realmService,
      containerService,
      notificationService,
      tokenService,
      contentService,
    );
  }
}
