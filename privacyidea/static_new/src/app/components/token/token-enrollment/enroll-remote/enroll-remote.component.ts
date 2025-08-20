import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { ErrorStateMatcher, MatOption } from "@angular/material/core";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatError, MatSelect } from "@angular/material/select";
import {
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface,
  RemoteServer
} from "../../../../services/privavyidea-server/privacyidea-server.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  RemoteApiPayloadMapper,
  RemoteEnrollmentData
} from "../../../../mappers/token-api-payload/remote-token-api-payload.mapper";

export class RemoteErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value.id === "" : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-remote",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatOption,
    MatSelect,
    MatCheckbox,
    MatError
  ],
  templateUrl: "./enroll-remote.component.html",
  styleUrl: "./enroll-remote.component.scss"
})
export class EnrollRemoteComponent implements OnInit {
  protected readonly enrollmentMapper: RemoteApiPayloadMapper = inject(
    RemoteApiPayloadMapper
  );
  protected readonly privacyideaServerService: PrivacyideaServerServiceInterface =
    inject(PrivacyideaServerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === "remote")?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  checkPinLocallyControl = new FormControl<boolean>(false, [
    Validators.required
  ]);
  remoteServerControl = new FormControl<RemoteServer | null>(null, [
    Validators.required
  ]);
  remoteSerialControl = new FormControl<string>("", [Validators.required]);
  remoteUserControl = new FormControl<string>("");
  remoteRealmControl = new FormControl<string>("");
  remoteResolverControl = new FormControl<string>("", [Validators.required]);

  remoteForm = new FormGroup({
    checkPinLocally: this.checkPinLocallyControl,
    remoteServer: this.remoteServerControl,
    remoteSerial: this.remoteSerialControl,
    remoteUser: this.remoteUserControl,
    remoteRealm: this.remoteRealmControl,
    remoteResolver: this.remoteResolverControl
  });

  remoteServerOptions = this.privacyideaServerService.remoteServerOptions;
  remoteErrorStateMatcher = new RemoteErrorStateMatcher();

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      checkPinLocally: this.checkPinLocallyControl,
      remoteServer: this.remoteServerControl,
      remoteSerial: this.remoteSerialControl,
      remoteUser: this.remoteUserControl,
      remoteRealm: this.remoteRealmControl,
      remoteResolver: this.remoteResolverControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData
  ): Observable<EnrollmentResponse | null> => {
    if (this.remoteForm.invalid) {
      this.remoteForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: RemoteEnrollmentData = {
      ...basicOptions,
      type: "remote",
      checkPinLocally: !!this.checkPinLocallyControl.value,
      remoteServer: this.remoteServerControl.value,
      remoteSerial: this.remoteSerialControl.value ?? "",
      remoteUser: this.remoteUserControl.value ?? "",
      remoteRealm: this.remoteRealmControl.value ?? "",
      remoteResolver: this.remoteResolverControl.value ?? ""
    };

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
