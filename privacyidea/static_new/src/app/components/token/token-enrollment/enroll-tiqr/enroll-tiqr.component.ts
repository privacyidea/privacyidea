import {
  Component,
  computed,
  EventEmitter,
  OnInit,
  Output,
} from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { SystemService } from '../../../../services/system/system.service';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Observable } from 'rxjs';

export interface TiqrEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'tiqr';
  // No type-specific fields for initialization via EnrollmentOptions
  // TIQR-specific data (tiqr.infoUrl etc.) comes from the system configuration
  // and are not passed directly as EnrollmentOptions.
}
@Component({
  selector: 'app-enroll-tiqr',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tiqr.component.html',
  styleUrl: './enroll-tiqr.component.scss',
})
export class EnrollTiqrComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'tiqr')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  defaultTiQRIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(
      cfg?.['tiqr.infoUrl'] &&
      cfg?.['tiqr.logoUrl'] &&
      cfg?.['tiqr.regServer']
    );
  });

  tiqrForm = new FormGroup({}); // No specific controls for TIQR

  constructor(
    private systemService: SystemService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    const enrollmentData: TiqrEnrollmentOptions = {
      ...basicOptions,
      type: 'tiqr',
    };
    return this.tokenService.enrollToken(enrollmentData);
  };
}
