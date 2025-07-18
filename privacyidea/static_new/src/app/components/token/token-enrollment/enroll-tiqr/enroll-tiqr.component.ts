import {
  Component,
  computed,
  EventEmitter,
  Inject,
  OnInit,
  Output,
} from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {
  SystemService,
  SystemServiceInterface,
} from '../../../../services/system/system.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';

import { Observable } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { TiqrApiPayloadMapper } from '../../../../mappers/token-api-payload/tiqr-token-api-payload.mapper';

export interface TiqrEnrollmentOptions extends TokenEnrollmentData {
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
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
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
    private enrollmentMapper: TiqrApiPayloadMapper,
    @Inject(SystemService)
    private systemService: SystemServiceInterface,
    @Inject(TokenService)
    private tokenService: TokenServiceInterface,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    const enrollmentData: TiqrEnrollmentOptions = {
      ...basicOptions,
      type: 'tiqr',
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
