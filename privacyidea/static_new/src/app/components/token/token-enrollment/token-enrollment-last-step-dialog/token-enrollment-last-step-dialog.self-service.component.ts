import { Component, Inject } from '@angular/core';
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
import { TokenService } from '../../../../services/token/token.service';
import { ContentService } from '../../../../services/content/content.service';
import { UserData } from '../../../../services/user/user.service';
import { EnrollmentResponse } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { TokenEnrollmentLastStepDialogComponent } from './token-enrollment-last-step-dialog.component';

export type TokenEnrollmentLastStepDialogData = {
  response: EnrollmentResponse;
  enrollToken: () => void;
  user: UserData | null;
  userRealm: string;
  onlyAddToRealm: boolean;
};

@Component({
  selector: 'app-token-enrollment-last-step-dialog-self-service',
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
  ],
  templateUrl:
    './token-enrollment-last-step-dialog.self-service.component.html',
  styleUrl: './token-enrollment-last-step-dialog.component.scss',
})
export class TokenEnrollmentLastStepDialogSelfServiceComponent extends TokenEnrollmentLastStepDialogComponent {
  protected override readonly Object = Object;

  constructor(
    protected override tokenService: TokenService,
    protected override contentService: ContentService,
    protected override dialogRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    public override data: TokenEnrollmentLastStepDialogData,
  ) {
    super(tokenService, contentService, dialogRef, data);
  }
}
