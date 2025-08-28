import { Component, computed, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { TiqrApiPayloadMapper } from "../../../../mappers/token-api-payload/tiqr-token-api-payload.mapper";

export interface TiqrEnrollmentOptions extends TokenEnrollmentData {
  type: "tiqr";
}

@Component({
  selector: "app-enroll-tiqr",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-tiqr.component.html",
  styleUrl: "./enroll-tiqr.component.scss"
})
export class EnrollTiqrComponent implements OnInit {
  protected readonly enrollmentMapper: TiqrApiPayloadMapper = inject(TiqrApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  defaultTiQRIsSet = computed(() => {
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(cfg?.["tiqr.infoUrl"] && cfg?.["tiqr.logoUrl"] && cfg?.["tiqr.regServer"]);
  });

  tiqrForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    const enrollmentData: TiqrEnrollmentOptions = {
      ...basicOptions,
      type: "tiqr"
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
