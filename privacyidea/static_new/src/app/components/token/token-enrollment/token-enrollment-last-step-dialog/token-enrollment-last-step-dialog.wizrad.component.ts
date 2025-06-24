import { Component, Inject, WritableSignal } from '@angular/core';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
} from '@angular/material/expansion';
import { MatIcon } from '@angular/material/icon';
import { TokenEnrollmentLastStepDialogComponent } from './token-enrollment-last-step-dialog.component';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { ContentService } from '../../../../services/content/content.service';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer } from '@angular/platform-browser';
import { map } from 'rxjs';
import { UserData } from '../../../../services/user/user.service';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-token-enrollment-second-step-dialog-wizard',
  imports: [
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogTitle,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton,
    AsyncPipe,
  ],
  templateUrl: './token-enrollment-last-step-dialog.wizard.component.html',
  styleUrl: './token-enrollment-last-step-dialog.component.scss',
})
export class TokenEnrollmentSecondStepDialogWizardComponent extends TokenEnrollmentLastStepDialogComponent {
  readonly postTopHtml$ = this.http
    .get('/customize/token-enrollment.wizard.post.top.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  readonly postBottomHtml$ = this.http
    .get('/customize/token-enrollment.wizard.post.bottom.html', {
      responseType: 'text',
    })
    .pipe(map((raw) => this.sanitizer.bypassSecurityTrustHtml(raw)));

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer,
    tokenService: TokenService,
    contentService: ContentService,
    dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    data: {
      enrollToken: () => void;
      onlyAddToRealm: boolean;
      response: EnrollmentResponse;
      userRealm: string;
      user: UserData;
    },
  ) {
    super(tokenService, contentService, dialogRef, data);
  }
}
