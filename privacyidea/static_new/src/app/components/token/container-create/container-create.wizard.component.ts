import { AsyncPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButton, MatIconButton } from '@angular/material/button';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatOption } from '@angular/material/core';
import { MatDialog } from '@angular/material/dialog';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatSelect } from '@angular/material/select';
import { DomSanitizer } from '@angular/platform-browser';
import { map } from 'rxjs';
import { ContainerService } from '../../../services/container/container.service';
import { ContentService } from '../../../services/content/content.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { RealmService } from '../../../services/realm/realm.service';
import { TokenService } from '../../../services/token/token.service';
import { UserService } from '../../../services/user/user.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../services/version/version.service';
import { ContainerCreateComponent } from './container-create.component';

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
    @Inject(VersioningService)
    versioningService: VersioningServiceInterface,
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
